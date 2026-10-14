#!/usr/bin/env node
// Aperçu d'une page sur trois téléphones et un ordinateur : une capture par appareil, prise par
// le Chromium de Playwright du projet (aucun navigateur à installer en plus), pour que Claude
// « voie » une page ou une fenêtre comme les utilisateurs.
//
// Usage, depuis le dossier du front :
//   node <ce script> <chemin ou URL> [--compte member] [--attendre '[role=dialog]']
//                    [--sortie dossier] [--nom prefixe] [--pleine-page]
//
// Lit `.playwright/config` (clé=valeur) et `.playwright/token` à la racine du repo :
//   url=http://localhost:3000        base des chemins relatifs
//   login_<compte>=identifiant       compte de --compte <compte> (--compte defaut : login=)
//   login_path=/auth/portal          page de connexion (défaut) ; login_suivant=next : paramètre
//                                    de retour vers la page visée après connexion
//   champ_identifiant / champ_mot_de_passe : sélecteurs des champs (défauts : autocomplete)
//   pret=html[data-hydrated]         élément posé quand l'app a pris la main (hydratation) ;
//                                    sans lui, un formulaire envoyé trop tôt part en GET natif
// Les captures vont dans `.playwright/captures/apercu/` par défaut.
import { existsSync, mkdirSync, readFileSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { createRequire } from 'node:module'
import { join, resolve } from 'node:path'

// Appareils retenus : les gammes les plus vendues au monde et les largeurs d'écran les plus
// répandues. Les préréglages viennent de Playwright ; tous tournent dans Chromium (WebKit n'est
// pas installé) : c'est la mise en page qui est vérifiée, pas le moteur de Safari.
const APPAREILS = [
  { nom: 'iphone-16', preset: 'iPhone 16' },                 // 393 px, gamme iPhone
  { nom: 'galaxy-a55', preset: 'Galaxy A55' },               // série A de Samsung
  { nom: 'galaxy-s24', preset: 'Galaxy S24' },               // 360 px, largeur mobile la plus courante
  { nom: 'ordinateur', viewport: { width: 1920, height: 1080 } } // résolution de bureau la plus courante
]
const DELAI_RENDU_MS = 1500
const DELAI_ATTENTE_MS = 15000

function lireArguments(argv) {
  const options = { cible: null, compte: null, attendre: null, sortie: null, nom: 'apercu', pleinePage: false }
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]
    if (argument === '--compte') options.compte = argv[++index]
    else if (argument === '--attendre') options.attendre = argv[++index]
    else if (argument === '--sortie') options.sortie = argv[++index]
    else if (argument === '--nom') options.nom = argv[++index]
    else if (argument === '--pleine-page') options.pleinePage = true
    else options.cible = argument
  }
  if (!options.cible) throw new Error('Chemin ou URL de la page manquant.')
  return options
}

function racineDuRepo(depart) {
  let dossier = resolve(depart)
  while (!existsSync(join(dossier, '.git'))) {
    const parent = resolve(dossier, '..')
    if (parent === dossier) return resolve(depart)
    dossier = parent
  }
  return dossier
}

function lireConfig(racine) {
  const fichier = join(racine, '.playwright', 'config')
  const config = {}
  if (!existsSync(fichier)) return config
  for (const ligne of readFileSync(fichier, 'utf8').split('\n')) {
    const propre = ligne.trim()
    if (!propre || propre.startsWith('#') || !propre.includes('=')) continue
    const position = propre.indexOf('=')
    config[propre.slice(0, position).trim()] = propre.slice(position + 1).trim()
  }
  return config
}

// Connexion par la page de connexion, avec la page visée en paramètre de retour (`next`) : on y
// arrive connecté sans recharger, la session tenue en mémoire par l'app reste valide.
async function seConnecter(page, base, config, racine, compte, cible) {
  const cle = compte === 'defaut' ? 'login' : `login_${compte}`
  const identifiant = config[cle]
  if (!identifiant) throw new Error(`Pas de ${cle}= dans .playwright/config.`)
  const motDePasse = readFileSync(join(racine, '.playwright', 'token'), 'utf8').trim()
  const portail = config.login_path ?? '/auth/portal'
  const adresse = new URL(portail, base)
  adresse.searchParams.set(config.login_suivant ?? 'next', cible.pathname + cible.search)
  await page.goto(adresse.href, { waitUntil: 'load' })
  await attendrePret(page, config)
  await page.locator(config.champ_identifiant ?? 'input[autocomplete=username]').first().fill(identifiant)
  const champ = page.locator(config.champ_mot_de_passe ?? 'input[autocomplete=current-password]').first()
  await champ.fill(motDePasse)
  await champ.press('Enter')
  await page.waitForURL(url => !url.pathname.startsWith(portail), { timeout: DELAI_ATTENTE_MS })
}

async function attendrePret(page, config) {
  if (config.pret) await page.locator(config.pret).waitFor({ state: 'attached', timeout: DELAI_ATTENTE_MS })
}

// Une seule page, qui prend tour à tour la forme de chaque appareil (taille, densité, tactile,
// navigateur mobile) : une connexion par lancement, et une fenêtre ouverte une fois se capture
// sur les quatre. Limite : ce que le serveur rend selon le navigateur reste celui du premier
// chargement ; la mise en page, elle, suit chaque écran.
async function emuler(session, devices, appareil, agentParDefaut) {
  const profil = appareil.preset ? devices[appareil.preset] : { viewport: appareil.viewport, deviceScaleFactor: 1 }
  await session.send('Emulation.setDeviceMetricsOverride', {
    width: profil.viewport.width,
    height: profil.viewport.height,
    deviceScaleFactor: profil.deviceScaleFactor ?? 1,
    mobile: Boolean(profil.isMobile)
  })
  await session.send('Emulation.setTouchEmulationEnabled', { enabled: Boolean(profil.hasTouch) })
  await session.send('Emulation.setUserAgentOverride', { userAgent: profil.userAgent ?? agentParDefaut })
}

async function capturer(page, session, devices, appareil, options, sortie, agentParDefaut) {
  await emuler(session, devices, appareil, agentParDefaut)
  await page.waitForTimeout(DELAI_RENDU_MS)
  const fichier = join(sortie, `${options.nom}-${appareil.nom}.png`)
  await page.screenshot({ path: fichier, fullPage: options.pleinePage })
  const debordement = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
  return { fichier, debordement }
}

// Le Chromium attendu par la version de Playwright du projet s'installe au premier lancement
// (quelques secondes ensuite) : un poste neuf ou une montée de Playwright n'a rien à faire.
async function lancerChromium(chromium) {
  try {
    return await chromium.launch()
  } catch (erreur) {
    if (!String(erreur.message).includes('Executable doesn')) throw erreur
    execFileSync('npx', ['playwright', 'install', 'chromium'], { stdio: 'ignore' })
    return chromium.launch()
  }
}

async function main() {
  const options = lireArguments(process.argv.slice(2))
  const racine = racineDuRepo(process.cwd())
  const config = lireConfig(racine)
  const exiger = createRequire(join(process.cwd(), 'package.json'))
  const { chromium, devices } = exiger('@playwright/test')
  const base = config.url ?? 'http://localhost:3000'
  const url = new URL(options.cible, base).href
  const sortie = resolve(options.sortie ?? join(racine, '.playwright', 'captures', 'apercu'))
  mkdirSync(sortie, { recursive: true })
  const navigateur = await lancerChromium(chromium)
  try {
    // Sans taille imposée par Playwright : c'est l'émulation de chaque appareil qui la donne.
    const contexte = await navigateur.newContext({ locale: 'fr-FR', viewport: null })
    const page = await contexte.newPage()
    const session = await contexte.newCDPSession(page)
    const cible = new URL(url)
    if (options.compte !== null) await seConnecter(page, base, config, racine, options.compte, cible)
    else await page.goto(url, { waitUntil: 'load', timeout: DELAI_ATTENTE_MS * 2 })
    await attendrePret(page, config)
    if (options.attendre) await page.locator(options.attendre).first().waitFor({ timeout: DELAI_ATTENTE_MS })
    const agentParDefaut = await page.evaluate(() => navigator.userAgent)
    for (const appareil of APPAREILS) {
      const { fichier, debordement } = await capturer(page, session, devices, appareil, options, sortie, agentParDefaut)
      console.log(`${appareil.nom}\t${fichier}${debordement ? '\tDÉBORDEMENT HORIZONTAL' : ''}`)
    }
  } finally {
    await navigateur.close()
  }
}

main().catch((erreur) => {
  console.error(`apercu : ${erreur.message}`)
  process.exit(1)
})
