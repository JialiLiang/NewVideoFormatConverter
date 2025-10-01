export type CreatorType = 'internal' | 'freelancer' | 'ramdam' | 'influencer';
export type HookOption = 'any' | 'come' | 'UGC' | 'text' | 'emoji' | 'nonono' | 'ASMR' | 'AIUGC' | 'custom';
export type VoiceOption = 'any' | 'null' | 'tom' | 'doja' | 'chris' | 'human' | 'custom';
export type MusicOption = 'any' | 'lofi' | 'kpop' | 'hiphop' | '90s' | 'trend' | 'custom';
export type DimensionOption = 'PO' | 'SQ' | 'LS';
export type FeatureTag =
  | 'AIBG'
  | 'IGSTORY'
  | 'LOGO'
  | 'ANIM'
  | 'MIX'
  | 'AIFILL'
  | 'RETOUCH'
  | 'IMGT-CHANGE'
  | 'IMGT-MODEL'
  | 'IMGT-STAGE'
  | 'IMGT-BEAUTIFY'
  | 'RnD';

type HookInputs = {
  hookText?: string;
  hookUgc?: string;
  hookCustom?: string;
};

type VoiceInputs = {
  voiceName?: string;
  voScript?: string;
};

type MusicInputs = {
  musicCustom?: string;
};

export interface CreativeNameFormState extends HookInputs, VoiceInputs, MusicInputs {
  creatorType: CreatorType;
  creatorName: string;
  filename: string;
  creativeNumber: number;
  hook: HookOption;
  voiceOver: VoiceOption;
  music: MusicOption;
  dimension: DimensionOption;
  feature: FeatureTag;
  language: string;
}

export interface CreativeNamePreview {
  preview: string;
  sampleWithId: string;
}

export interface ValidationCheck {
  label: string;
  value: string;
  isValid: boolean;
}

export interface NameValidationResult {
  isValid: boolean;
  message: string;
  structureChecks: ValidationCheck[];
  contentChecks: ValidationCheck[];
  format: 'admanage' | 'admanage-compact' | 'basic' | 'invalid';
}

const FEATURE_OPTIONS: FeatureTag[] = [
  'AIBG',
  'IGSTORY',
  'LOGO',
  'ANIM',
  'MIX',
  'AIFILL',
  'RETOUCH',
  'IMGT-CHANGE',
  'IMGT-MODEL',
  'IMGT-STAGE',
  'IMGT-BEAUTIFY',
  'RnD',
];

const LANGUAGE_OPTIONS = [
  'en',
  'fr',
  'pt',
  'es',
  'ja',
  'ko',
  'ar',
  'zh',
  'de',
  'hi',
  'id',
  'it',
  'ms',
  'nl',
  'pl',
  'th',
  'tl',
  'tr',
  'vi',
] as const;

const VALID_HOOKS: HookOption[] = ['any', 'come', 'UGC', 'text', 'emoji', 'nonono', 'ASMR', 'AIUGC', 'custom'];
const VALID_VOICES: VoiceOption[] = ['any', 'null', 'tom', 'doja', 'chris', 'human', 'custom'];
const VALID_MUSIC: MusicOption[] = ['any', 'lofi', 'kpop', 'hiphop', '90s', 'trend', 'custom'];

const FORBIDDEN_FILENAME_CHARS = /[!"#$%&'()*+,/:;<=>?[\\\]^`{|}~]/g;
const TRAILING_ITERATION_REGEX = /-ITE-\d+$/i;
const DIMENSION_TOKEN_SET = new Set<DimensionOption>(['PO', 'SQ', 'LS']);
const ITERATION_DATE_REGEX = /^\d{8}$/;

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

export const formatToPascalCase = (text: string): string => {
  if (!text) return '';
  const cleaned = text.replace(FORBIDDEN_FILENAME_CHARS, ' ').trim();
  if (!cleaned) return '';
  let words = cleaned.split(/\s+/);
  if (words.length === 1 && /[A-Z]/.test(words[0].slice(1))) {
    words = words[0].split(/(?=[A-Z])/).filter(Boolean);
  }
  return words
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join('');
};

const sanitizeCreativeNumber = (value: number): number => clamp(Math.round(value || 1), 1, 999);

const sanitizeLanguage = (code: string): string => {
  const trimmed = code ? code.trim() : '';
  return trimmed || 'language';
};

const sanitizeCreatorName = (raw: string): string => formatToPascalCase(raw).trim();

const sanitizeFilename = (raw: string, creativeNumber: number): string => {
  const fallback = '[filename]';
  if (!raw || raw === fallback) return fallback;
  const noSuffix = raw.replace(/-\d+\s*$/, '').trim();
  const formatted = formatToPascalCase(noSuffix);
  if (!formatted) return fallback;
  return `${formatted}-${sanitizeCreativeNumber(creativeNumber)}`;
};

const buildHookPart = (hook: HookOption, inputs: HookInputs): string => {
  if (hook === 'text' && inputs.hookText) {
    return `HOOK-text-${formatToPascalCase(inputs.hookText)}`;
  }
  if (hook === 'UGC' && inputs.hookUgc) {
    return `HOOK-ugc-${inputs.hookUgc.trim()}`;
  }
  if (hook === 'custom' && inputs.hookCustom) {
    return `HOOK-${formatToPascalCase(inputs.hookCustom)}`;
  }
  return `HOOK-${hook}`;
};

const buildVoicePart = (voice: VoiceOption, inputs: VoiceInputs): string => {
  const baseVoice = voice === 'custom' ? formatToPascalCase(inputs.voiceName ?? '') : voice;
  const safeVoice = baseVoice || '[voice]';
  if (voice === 'null') {
    return `VO-${safeVoice}`;
  }
  const script = inputs.voScript ? formatToPascalCase(inputs.voScript) : '';
  return script ? `VO-${safeVoice}-${script}` : `VO-${safeVoice}`;
};

const buildMusicPart = (music: MusicOption, custom?: string): string => {
  if (music === 'custom' && custom) {
    return `MUSIC-${formatToPascalCase(custom)}`;
  }
  return `MUSIC-${music}`;
};

export const TODAY_YYYYMMDD = (() => {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${d}${m}${y}`;
})();

export const buildCreativeName = (state: CreativeNameFormState): CreativeNamePreview => {
  const {
    creatorType,
    creatorName,
    filename,
    creativeNumber,
    hook,
    hookText,
    hookUgc,
    hookCustom,
    voiceOver,
    voiceName,
    voScript,
    music,
    musicCustom,
    dimension,
    feature,
    language,
  } = state;

  const cleanFilename = sanitizeFilename(filename, creativeNumber);
  const cleanCreatorName = sanitizeCreatorName(creatorName);

  let prefix: string;
  if (creatorType === 'internal') {
    prefix = `${creatorType}_${cleanFilename}`;
  } else if (creatorType) {
    const namePart = cleanCreatorName || '[name]';
    prefix = `${creatorType}-${namePart}_${cleanFilename}`;
  } else {
    prefix = `[creator-type]_${cleanFilename}`;
  }

  const hookPart = buildHookPart(hook, { hookText, hookUgc, hookCustom });
  const voicePart = buildVoicePart(voiceOver, { voiceName, voScript });
  const musicPart = buildMusicPart(music, musicCustom);
  const dimensionPart = dimension || '[dim]';
  const tagsBlock = `${hookPart}_${voicePart}_${musicPart}_${dimensionPart}`;

  const featurePart = feature ? `[${feature}]` : '[AIBG]';
  const languagePart = `[${sanitizeLanguage(language)}]`;

  const preview = `${prefix}_${tagsBlock}_${featurePart}_${languagePart}`;
  const sample = `12345_Jiali_${preview}_${TODAY_YYYYMMDD}`;

  return { preview, sampleWithId: sample };
};

const isIterationSuffixStart = (token: string): boolean =>
  token.startsWith('HOOK-') || token.startsWith('VO-') || token.startsWith('MUSIC-') || DIMENSION_TOKEN_SET.has(token as DimensionOption);

const sanitizeIterationSegment = (value: string): string => value.trim().replace(/^[-_\s]+|[-_\s]+$/g, '');
export const generateIterationName = (original: string, iteration: number): string | null => {
  const trimmed = original.trim();
  if (!trimmed) return null;

  const parts = trimmed.split('_').filter(Boolean);
  const suffixStartIndex = parts.findIndex(isIterationSuffixStart);
  if (suffixStartIndex === -1) return null;

  const prefixTokens = parts.slice(0, suffixStartIndex);
  const suffixTokens = parts.slice(suffixStartIndex).filter((token) => !ITERATION_DATE_REGEX.test(token));

  const safePieces = prefixTokens
    .map((segment) => sanitizeIterationSegment(segment).replace(TRAILING_ITERATION_REGEX, ''))
    .filter((segment) => segment.length > 0);

  const rawFilename = safePieces.length > 0 ? safePieces.join('-').replace(/--+/g, '-') : '[filename]';
  const baseWithoutIteration = rawFilename.replace(TRAILING_ITERATION_REGEX, '');
  const cleanedBase = baseWithoutIteration.replace(/-\d+$/i, '').replace(/-+$/g, '');
  const safeIteration = clamp(Math.round(iteration || 1), 1, 99);
  const baseForIteration = (cleanedBase || rawFilename).replace(/-+$/g, '');
  const filenameWithIteration = `${baseForIteration}-ITE-${safeIteration}`;

  if (suffixTokens.length === 0) {
    return `internal_${filenameWithIteration}`;
  }

  return `internal_${filenameWithIteration}_${suffixTokens.join('_')}`;
};

const checkStructure = (label: string, value: string, isValid: boolean): ValidationCheck => ({
  label,
  value,
  isValid,
});

const asBracketless = (value: string) => value.replace(/^\[|\]$/g, '');

export const validateCreativeName = (name: string): NameValidationResult => {
  const trimmed = name.trim();
  if (!trimmed) {
    return {
      isValid: false,
      message: 'Name is empty',
      structureChecks: [],
      contentChecks: [],
      format: 'invalid',
    };
  }

  const parts = trimmed.split('_');
  const hasId = /^\d+$/.test(parts[0]);
  const hasDate = /^\d{8}$/.test(parts[parts.length - 1]);
  const hasEmptyTags = parts.some((part) => part === '-');

  const isAdmanage = hasId && parts.length >= 9 && parts.length <= 11 && !hasEmptyTags;
  const isAdmanageCompact = hasId && hasDate && parts.length === 11 && hasEmptyTags;
  const isBasic = !hasId && parts.length >= 7 && parts.length <= 9;

  const structureChecks: ValidationCheck[] = [];
  const contentChecks: ValidationCheck[] = [];
  let format: NameValidationResult['format'] = 'invalid';

  const addTagChecks = (hookPart: string, voPart: string, musicPart: string, dimPart: string) => {
    structureChecks.push(checkStructure('HOOK tag', hookPart, hookPart.startsWith('HOOK-')));
    structureChecks.push(checkStructure('VO tag', voPart, voPart.startsWith('VO-')));
    structureChecks.push(checkStructure('MUSIC tag', musicPart, musicPart.startsWith('MUSIC-')));
    structureChecks.push(checkStructure('DIM tag', dimPart, ['PO', 'SQ', 'LS'].includes(dimPart)));

    contentChecks.push(validateHookContent(hookPart));
    contentChecks.push(validateVoiceContent(voPart));
    contentChecks.push(validateMusicContent(musicPart));
  };

  if (isAdmanage) {
    format = 'admanage';
    structureChecks.push(checkStructure('Format', 'AdManage with optional date', true));
    structureChecks.push(checkStructure('Parts count', `${parts.length}`, parts.length >= 9 && parts.length <= 11));
    structureChecks.push(checkStructure('ID', parts[0], hasId));

    const creatorType = parts[2];
    const filename = parts[3];
    const validCreatorTypes: CreatorType[] = ['internal', 'freelancer', 'ramdam', 'influencer'];
    if (creatorType === 'internal') {
      structureChecks.push(checkStructure('Creator type', creatorType, validCreatorTypes.includes(creatorType as CreatorType)));
    } else {
      const hasTypePrefix = validCreatorTypes.some((type) => creatorType.startsWith(`${type}-`));
      structureChecks.push(checkStructure('Creator type + name', creatorType, hasTypePrefix));
    }
    structureChecks.push(checkStructure('Filename', filename, /^[A-Za-z0-9-]+$/.test(filename)));

    addTagChecks(parts[4], parts[5], parts[6], parts[7]);

    const featureIndex = parts.length === 9 ? 7 : 8;
    const languageIndex = parts.length === 9 ? 8 : 9;
    const feature = parts[featureIndex];
    const language = parts[languageIndex];

    structureChecks.push(
      checkStructure('Feature tag', feature, FEATURE_OPTIONS.includes(asBracketless(feature) as FeatureTag)),
    );
    const languageNormalized = asBracketless(language);
    structureChecks.push(
      checkStructure('Language', language, [...LANGUAGE_OPTIONS, ...LANGUAGE_OPTIONS.map((code) => code.toUpperCase())].includes(languageNormalized as any)),
    );

  } else if (isAdmanageCompact) {
    format = 'admanage-compact';
    structureChecks.push(checkStructure('Format', 'AdManage compact', true));
    structureChecks.push(checkStructure('Parts count', `${parts.length}`, true));
    structureChecks.push(checkStructure('ID', parts[0], true));

    addTagChecks(parts[4], parts[5], parts[6], parts[7]);

    const feature = parts[8];
    const language = parts[9];
    structureChecks.push(
      checkStructure('Feature tag', feature, FEATURE_OPTIONS.includes(asBracketless(feature) as FeatureTag)),
    );
    structureChecks.push(
      checkStructure('Language', language, [...LANGUAGE_OPTIONS, ...LANGUAGE_OPTIONS.map((code) => code.toUpperCase())].includes(asBracketless(language) as any)),
    );
  } else if (isBasic) {
    format = 'basic';
    structureChecks.push(checkStructure('Format', 'Basic (no ID/date)', true));
    structureChecks.push(checkStructure('Parts count', `${parts.length}`, parts.length >= 7 && parts.length <= 9));

    const creatorType = parts[0];
    structureChecks.push(
      checkStructure('Creator type', creatorType, ['internal', 'freelancer', 'ramdam', 'influencer'].includes(creatorType)),
    );
    const filename = parts[1];
    structureChecks.push(checkStructure('Filename', filename, /^[A-Za-z0-9-]+$/.test(filename)));

    addTagChecks(parts[2], parts[3], parts[4], parts[5]);

    const feature = parts[6];
    const language = parts[7];
    structureChecks.push(
      checkStructure('Feature tag', feature, FEATURE_OPTIONS.includes(asBracketless(feature) as FeatureTag)),
    );
    structureChecks.push(
      checkStructure('Language', language, [...LANGUAGE_OPTIONS, ...LANGUAGE_OPTIONS.map((code) => code.toUpperCase())].includes(asBracketless(language) as any)),
    );
  } else {
    return {
      isValid: false,
      message: 'Invalid structure detected',
      structureChecks: [checkStructure('Structure', trimmed, false)],
      contentChecks: [],
      format: 'invalid',
    };
  }

  const structureValid = structureChecks.every((c) => c.isValid);
  const contentValid = contentChecks.every((c) => c.isValid);

  return {
    isValid: structureValid && contentValid,
    message:
      structureValid && contentValid
        ? 'This creative name follows naming conventions.'
        : 'Issues detected. Review structure and content feedback.',
    structureChecks,
    contentChecks,
    format,
  };
};

const validateHookContent = (hookPart: string): ValidationCheck => {
  const value = hookPart.replace(/^HOOK-/, '');
  if (VALID_HOOKS.includes(value as HookOption)) {
    return { label: 'HOOK content', value, isValid: true };
  }
  if (value === '-' || value.startsWith('text-') || value.startsWith('ugc-') || value.length > 0) {
    return { label: 'HOOK content', value, isValid: true };
  }
  return { label: 'HOOK content', value, isValid: false };
};

const validateVoiceContent = (voPart: string): ValidationCheck => {
  const value = voPart.replace(/^VO-/, '');
  if (VALID_VOICES.includes(value as VoiceOption)) {
    return { label: 'VO content', value, isValid: true };
  }
  if (value === '-' || value.includes('-') || value.length > 2) {
    return { label: 'VO content', value, isValid: true };
  }
  return { label: 'VO content', value, isValid: false };
};

const validateMusicContent = (musicPart: string): ValidationCheck => {
  const value = musicPart.replace(/^MUSIC-/, '');
  if (VALID_MUSIC.includes(value as MusicOption)) {
    return { label: 'MUSIC content', value, isValid: true };
  }
  if (value === '-' || value.length > 2) {
    return { label: 'MUSIC content', value, isValid: true };
  }
  return { label: 'MUSIC content', value, isValid: false };
};

export const defaultCreativeState: CreativeNameFormState = {
  creatorType: 'internal',
  creatorName: '',
  filename: '',
  creativeNumber: 1,
  hook: 'any',
  hookText: '',
  hookUgc: '',
  hookCustom: '',
  voiceOver: 'any',
  voiceName: '',
  voScript: '',
  music: 'any',
  musicCustom: '',
  dimension: 'PO',
  feature: 'AIBG',
  language: 'en',
};

export const creatorTypeOptions: { value: CreatorType; label: string }[] = [
  { value: 'internal', label: 'Internal' },
  { value: 'freelancer', label: 'Freelancer' },
  { value: 'ramdam', label: 'Ramdam' },
  { value: 'influencer', label: 'Influencer' },
];

export const hookOptions: { value: HookOption; label: string }[] = [
  { value: 'any', label: 'any' },
  { value: 'come', label: 'come' },
  { value: 'UGC', label: 'UGC handle' },
  { value: 'text', label: 'Script text' },
  { value: 'emoji', label: 'emoji' },
  { value: 'nonono', label: 'nonono' },
  { value: 'ASMR', label: 'ASMR' },
  { value: 'AIUGC', label: 'AIUGC' },
  { value: 'custom', label: 'Custom hook' },
];

export const voiceOptions: { value: VoiceOption; label: string }[] = [
  { value: 'any', label: 'any' },
  { value: 'null', label: 'null' },
  { value: 'tom', label: 'Tom' },
  { value: 'doja', label: 'Doja' },
  { value: 'chris', label: 'Chris' },
  { value: 'human', label: 'Human' },
  { value: 'custom', label: 'Custom voice' },
];

export const musicOptions: { value: MusicOption; label: string }[] = [
  { value: 'any', label: 'any' },
  { value: 'lofi', label: 'lofi (ambience)' },
  { value: 'kpop', label: 'kpop' },
  { value: 'hiphop', label: 'hiphop' },
  { value: '90s', label: '90s' },
  { value: 'trend', label: 'trend' },
  { value: 'custom', label: 'Custom song' },
];

export const dimensionOptions: { value: DimensionOption; label: string }[] = [
  { value: 'PO', label: 'PO - Portrait (9:16)' },
  { value: 'SQ', label: 'SQ - Square (1:1)' },
  { value: 'LS', label: 'LS - Landscape (16:9)' },
];

export const featureOptions: FeatureTag[] = FEATURE_OPTIONS;

export const languageOptions: { value: string; label: string }[] = LANGUAGE_OPTIONS.map((code) => ({
  value: code,
  label: code,
}));
