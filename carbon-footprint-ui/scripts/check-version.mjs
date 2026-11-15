// Prüft, dass die Version aus package.json als erster Eintrag im Changelog der README steht.
// Wird vor jedem Build ausgeführt; Versionen mit tools/bump_version.py im Projektordner erhöhen.
import { readFileSync } from 'node:fs'

const { version } = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf-8'))
const readme = readFileSync(new URL('../README.md', import.meta.url), 'utf-8')
const changelog = readme.split('## Changelog')[1] ?? ''
const first = changelog.match(/^### (\d+\.\d+\.\d+)/m)?.[1]

if (!/^\d+\.\d+\.\d+$/.test(version)) {
  console.error(`Version ${version} in package.json ist keine SemVer-Version`)
  process.exit(1)
}
if (first !== version) {
  console.error(`package.json hat Version ${version}, der neueste Changelog-Eintrag ist ${first ?? 'keiner'}.`)
  console.error('Version mit "python tools/bump_version.py ui <major|minor|patch> <Beschreibung>" erhöhen.')
  process.exit(1)
}
// docker-compose.yml im Projektordner (falls vorhanden) muss dieselbe Version verwenden
try {
  const compose = readFileSync(new URL('../../docker-compose.yml', import.meta.url), 'utf-8')
  if (!compose.includes(`image: dppviewer-ui:${version}`)) {
    console.error(`docker-compose.yml verwendet nicht dppviewer-ui:${version} (tools/bump_version.py verwenden)`)
    process.exit(1)
  }
} catch (error) {
  if (error.code !== 'ENOENT') throw error
}
console.log(`Version ${version} ok`)
