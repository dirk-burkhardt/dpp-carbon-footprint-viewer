import type { components } from '@/lib/api/AssetAdministrationShellRegistry'

const userLanguages = (navigator.languages || [navigator.language] || [(navigator as any).userLanguage as string]);

// Preferred languages, mostly as ISO 639, and english as fallback
const preferredLanguages = [
  ...userLanguages.map(x => x.split("-", 1)[0].toLowerCase()).filter(x => x.length == 2),
  "en"
];

export default function lang(
  languageStrings?: components["schemas"]["AbstractLangString"][]
) {
  if (!languageStrings || !languageStrings.length) {
    return "";
  }
  for (const l of preferredLanguages) {
    for (const lString of languageStrings) {
      if (lString.language.toLowerCase() === l) {
        return lString.text;
      }
    }
  }
  return languageStrings[0].text;
}

export function langOrString(
  languageStrings?: components["schemas"]["AbstractLangString"][] | string
) {
  if (typeof  languageStrings === "string") {
    return languageStrings;
  }
  return lang(languageStrings);
}
