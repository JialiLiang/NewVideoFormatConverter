export interface LanguageEntry {
  code: string;
  name: string;
  preset?: 'top5';
}

export const LANGUAGES: LanguageEntry[] = [
  { code: 'en', name: 'English', preset: 'top5' },
  { code: 'fr', name: 'French', preset: 'top5' },
  { code: 'pt', name: 'Portuguese (Brazilian)', preset: 'top5' },
  { code: 'es', name: 'Spanish', preset: 'top5' },
  { code: 'ja', name: 'Japanese', preset: 'top5' },
  { code: 'ko', name: 'Korean', preset: 'top5' },
  { code: 'ar', name: 'Arabic' },
  { code: 'hi', name: 'Hindi' },
  { code: 'vi', name: 'Vietnamese' },
  { code: 'tl', name: 'Filipino' },
  { code: 'ms', name: 'Malay' },
  { code: 'zh', name: 'Chinese' },
  { code: 'de', name: 'German' },
  { code: 'it', name: 'Italian' },
  { code: 'id', name: 'Indonesian' },
  { code: 'tr', name: 'Turkish' },
  { code: 'pl', name: 'Polish' },
  { code: 'th', name: 'Thai' },
  { code: 'nl', name: 'Dutch' },
];

export const TOP5_LANG_CODES = LANGUAGES.filter((lang) => lang.preset === 'top5').map((lang) => lang.code);

export const languageName = (code: string) =>
  LANGUAGES.find((lang) => lang.code === code)?.name ?? code.toUpperCase();
