import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
  Container,
  Divider,
  FormControl,
  FormHelperText,
  FormLabel,
  Grid,
  GridItem,
  Heading,
  HStack,
  Icon,
  Select,
  Radio,
  RadioGroup,
  SimpleGrid,
  Slider,
  SliderFilledTrack,
  SliderThumb,
  SliderTrack,
  Spinner,
  Stack,
  Switch,
  Tab,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
  Tag,
  TagCloseButton,
  TagLabel,
  Text,
  Textarea,
  useColorModeValue,
  useToast,
} from '@chakra-ui/react';
import { isAxiosError } from 'axios';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { FiUploadCloud, FiTrash2, FiDownload, FiRefreshCcw, FiMusic, FiVideo, FiPlay } from 'react-icons/fi';
import {
  fetchVoices,
  generateVoiceovers,
  mixAudio,
  transcribeMedia,
  translateText,
  uploadCustomMusic,
  uploadDefaultMusic,
  uploadVideo,
} from '../api/adlocalizer';
import type { GenerateVoiceResponse, MixAudioResponse, ElevenLabsVoice } from '../api/adlocalizer';
import { resolveApiUrl } from '../api/client';
import { LANGUAGES, languageName, TOP5_LANG_CODES } from '../constants/languages';
import { FileDropZone } from '../components/FileDropZone';

const DEFAULT_MUSIC_OPTIONS = [
  { file: 'asitwasH.mp3', label: 'As It Was (Harry Styles)' },
  { file: 'dilemma.mp3', label: 'Dilemma' },
  { file: 'lastChristams.mp3', label: 'Last Christmas' },
  { file: 'rapbeatL.mp3', label: 'Rap Beat L' },
  { file: 'Violet.mp3', label: 'Violet' },
];

const VOICE_MODEL_OPTIONS = [
  { value: 'eleven_multilingual_v2', label: 'Multilingual v2 (balanced)' },
  { value: 'eleven_v3', label: 'ElevenLabs v3 (crisp beta)' },
];

const CURATED_VOICE_IDS = [
  'g60FwKJuhCJqbDCeuXjm', // Tom Cruise
  'E1c1pVuZVvPrme6B9ryw', // Doja Cat
  'GExuKsZoHWEY97I6fXSP', // Kanye
];

const CURATED_FALLBACKS: Record<string, ElevenLabsVoice> = {
  g60FwKJuhCJqbDCeuXjm: {
    id: 'g60FwKJuhCJqbDCeuXjm',
    name: 'Tom Cruise',
  },
  E1c1pVuZVvPrme6B9ryw: {
    id: 'E1c1pVuZVvPrme6B9ryw',
    name: 'Doja Cat',
  },
  GExuKsZoHWEY97I6fXSP: {
    id: 'GExuKsZoHWEY97I6fXSP',
    name: 'Kanye',
  },
};

const HERO_STATS = [
  { label: 'Formats', value: 'AdManage/Basics' },
  { label: 'Hooks', value: '8 presets' },
  { label: 'Locales', value: '18 languages' },
];

type Translations = Record<string, string>;

type AudioFiles = Record<string, string>;

type MixedVideos = Record<string, any>;

const formatFileSize = (sizeMb?: number) => {
  if (!sizeMb && sizeMb !== 0) return '';
  if (sizeMb >= 1) return `${sizeMb.toFixed(1)} MB`;
  return `${(sizeMb * 1024).toFixed(0)} KB`;
};

export const AdLocalizerPage = () => {
  const toast = useToast();
  const heroGradient = useColorModeValue(
    'linear(to-r, purple.500, pink.500)',
    'linear(to-r, rgba(112,76,255,0.7), rgba(236,72,153,0.5))',
  );
  const cardBg = useColorModeValue('white', 'rgba(19,18,40,0.85)');
  const subtleBg = useColorModeValue('purple.50', 'rgba(112,76,255,0.18)');
  const secondaryTextColor = useColorModeValue('gray.600', 'whiteAlpha.700');
  const helperTextColor = useColorModeValue('gray.500', 'whiteAlpha.600');

  const [transcriptionFile, setTranscriptionFile] = useState<File | null>(null);
  const [transcriptionLoading, setTranscriptionLoading] = useState(false);
  const [transcriptionText, setTranscriptionText] = useState('');
  const [textInput, setTextInput] = useState('');
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>(TOP5_LANG_CODES);
  const [translationMode, setTranslationMode] = useState<'faithful' | 'creative'>('creative');
  const [translateLoading, setTranslateLoading] = useState(false);
  const [translations, setTranslations] = useState<Translations>({});

  const [availableVoices, setAvailableVoices] = useState<ElevenLabsVoice[]>([]);
  const [voiceId, setVoiceId] = useState('');
  const [voiceModel, setVoiceModel] = useState('eleven_multilingual_v2');
  const [voicesLoading, setVoicesLoading] = useState(false);
  const [voicesError, setVoicesError] = useState<string | null>(null);
  const [voiceLoading, setVoiceLoading] = useState(false);
  const [audioFiles, setAudioFiles] = useState<AudioFiles>({});
  const [showAllVoices, setShowAllVoices] = useState(false);
  const featuredToggleText = useColorModeValue('purple.700', 'whiteAlpha.900');
  const featuredToggleHover = useColorModeValue('purple.100', 'rgba(112,76,255,0.25)');

  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [videoInfo, setVideoInfo] = useState<{ filename: string; size?: number } | null>(null);
  const [customMusicFile, setCustomMusicFile] = useState<File | null>(null);
  const [defaultMusicFile, setDefaultMusicFile] = useState<string>('');
  const [originalVolume, setOriginalVolume] = useState(0.5);
  const [voiceoverVolume, setVoiceoverVolume] = useState(1);
  const [useCustomMusic, setUseCustomMusic] = useState(false);
  const [addSubtitles, setAddSubtitles] = useState(false);
  const [subtitleStyle, setSubtitleStyle] = useState<string>('');
  const [availableSubtitleStyles, setAvailableSubtitleStyles] = useState<string[]>([]);
  const [mixing, setMixing] = useState(false);
  const [mixedVideos, setMixedVideos] = useState<MixedVideos>({});

  const [loadingMessage, setLoadingMessage] = useState<string | null>(null);


  const showToast = useCallback(
    (status: 'success' | 'error' | 'info' | 'warning', title: string, description?: string) => {
      toast({ status, title, description, duration: 4000, isClosable: true });
    },
    [toast],
  );

  useEffect(() => {
    let cancelled = false;
    const loadVoices = async () => {
      setVoicesLoading(true);
      setVoicesError(null);
      try {
        const response = await fetchVoices();
        if (cancelled) return;

        const voices = response?.voices ?? [];
        const uniqueVoices = Array.from(new Map(voices.map((voice) => [voice.id, voice])).values()).sort((a, b) =>
          a.name.localeCompare(b.name),
        );

        setAvailableVoices(uniqueVoices);

        const curatedAvailable = CURATED_VOICE_IDS.filter((id) =>
          uniqueVoices.some((voice) => voice.id === id),
        );

        const prioritizedFallback =
          response?.default_voice_id || curatedAvailable[0] || CURATED_VOICE_IDS[0] || uniqueVoices[0]?.id || '';

        if (prioritizedFallback) {
          setVoiceId((current) => {
            if (!current) return prioritizedFallback;
            const inApi = uniqueVoices.some((voice) => voice.id === current);
            const isCurated = CURATED_VOICE_IDS.includes(current);
            return inApi || isCurated ? current : prioritizedFallback;
          });
        }
      } catch (error) {
        if (!cancelled) {
          console.error('Unable to load ElevenLabs voices', error);
          setVoicesError('Unable to load ElevenLabs voices. Check your API key.');
        }
      } finally {
        if (!cancelled) {
          setVoicesLoading(false);
        }
      }
    };

    void loadVoices();

    return () => {
      cancelled = true;
    };
  }, []);

  const handleTranscribe = async () => {
    if (!transcriptionFile) {
      showToast('warning', 'Choose a media file to transcribe first');
      return;
    }
    setTranscriptionLoading(true);
    setLoadingMessage('Transcribing media... This may take a moment.');
    try {
      const response = await transcribeMedia(transcriptionFile);
      if (response.transcription) {
        setTranscriptionText(response.transcription);
        setTextInput(response.transcription);
        showToast('success', 'Transcription complete');
      } else {
        showToast('error', 'Unable to transcribe media', response.error);
      }
    } catch (error) {
      showToast('error', 'Transcription failed', (error as Error).message);
    } finally {
      setTranscriptionLoading(false);
      setLoadingMessage(null);
    }
  };

  const toggleLanguage = (code: string) => {
    setSelectedLanguages((prev) =>
      prev.includes(code) ? prev.filter((lang) => lang !== code) : [...prev, code],
    );
  };

  const selectAllLanguages = () => {
    setSelectedLanguages(LANGUAGES.map((lang) => lang.code));
  };

  const clearLanguages = () => {
    setSelectedLanguages([]);
  };

  const selectTop5 = () => {
    setSelectedLanguages(TOP5_LANG_CODES);
  };

  const handleTranslate = async () => {
    if (!textInput.trim()) {
      showToast('warning', 'Enter text to translate');
      return;
    }
    if (selectedLanguages.length === 0) {
      showToast('warning', 'Select at least one language');
      return;
    }

    setTranslateLoading(true);
    setLoadingMessage('Translating text into selected languages...');
    try {
      const response = await translateText({
        text: textInput,
        languages: selectedLanguages,
        translation_mode: translationMode,
      });
      if (response.translations) {
        setTranslations(response.translations);
        showToast('success', 'Translations ready');
      } else {
        showToast('error', 'Translation failed', response.error);
      }
    } catch (error) {
      showToast('error', 'Translation failed', (error as Error).message);
    } finally {
      setTranslateLoading(false);
      setLoadingMessage(null);
    }
  };

  const handleGenerateVoiceovers = async () => {
    if (!Object.keys(translations).length) {
      showToast('warning', 'Translate text before generating voiceovers');
      return;
    }
    if (!voiceId) {
      showToast('warning', 'Select a voice before generating voiceovers');
      return;
    }
    setVoiceLoading(true);
    setLoadingMessage('Generating voiceovers...');
    try {
      const payload = {
        translations,
        voice_id: voiceId,
        voice_model: voiceModel || undefined,
      };
      const response: GenerateVoiceResponse = await generateVoiceovers(payload);
      if (response.audio_files) {
        setAudioFiles(response.audio_files);
        showToast('success', 'Voiceovers ready');
        if (response.warnings && Object.keys(response.warnings).length > 0) {
          const warningLanguages = Object.keys(response.warnings)
            .map((code) => languageName(code))
            .join(', ');
          showToast('warning', 'Some voices skipped', `Issues for: ${warningLanguages}`);
        }
      } else {
        showToast('error', 'Voice generation failed', response.error);
      }
    } catch (error) {
      if (isAxiosError(error)) {
        const errorMessage = (error.response?.data?.error as string) ?? 'Voice generation request failed';
        const details = error.response?.data?.details;
        const detailHint = details && typeof details === 'object' ? Object.keys(details)[0] : null;
        const description = detailHint
          ? `${errorMessage} (${detailHint})`
          : errorMessage || error.message;
        showToast('error', 'Voice generation failed', description);
      } else {
        showToast('error', 'Voice generation failed', (error as Error).message);
      }
    } finally {
      setVoiceLoading(false);
      setLoadingMessage(null);
    }
  };

  const handleVideoUpload = async (file: File) => {
    setVideoFile(file);
    setLoadingMessage('Uploading video...');
    try {
      const response = await uploadVideo(file);
      if (response?.success || response?.filename) {
        setVideoInfo({ filename: response.filename || file.name, size: response.size_mb });
        showToast('success', 'Video ready for mixing', formatFileSize(response.size_mb));
      } else if (response.error) {
        showToast('error', 'Video upload failed', response.error);
      }
    } catch (error) {
      showToast('error', 'Video upload failed', (error as Error).message);
    } finally {
      setLoadingMessage(null);
    }
  };

  const handleMusicUpload = async (file: File) => {
    setCustomMusicFile(file);
    setUseCustomMusic(true);
    setLoadingMessage('Uploading custom music...');
    try {
      const response = await uploadCustomMusic(file);
      if (response.success || response.music_path) {
        showToast('success', 'Custom music ready');
      } else if (response.error) {
        showToast('error', 'Music upload failed', response.error);
      }
    } catch (error) {
      showToast('error', 'Music upload failed', (error as Error).message);
    } finally {
      setLoadingMessage(null);
    }
  };

  const handleSelectDefaultMusic = async (value: string) => {
    setDefaultMusicFile(value);
    if (!value) {
      return;
    }
    setLoadingMessage('Preparing default music...');
    try {
      await uploadDefaultMusic(value);
      setUseCustomMusic(true);
      setCustomMusicFile(null);
      showToast('success', 'Default music selected');
    } catch (error) {
      showToast('error', 'Default music failed', (error as Error).message);
    } finally {
      setLoadingMessage(null);
    }
  };

  const handleMixAudio = async () => {
    if (!videoFile) {
      showToast('warning', 'Upload a video before mixing audio');
      return;
    }
    if (!Object.keys(audioFiles).length) {
      showToast('warning', 'Generate voiceovers before mixing audio');
      return;
    }

    setMixing(true);
    setLoadingMessage('Mixing audio and rendering videos...');
    try {
      const response: MixAudioResponse = await mixAudio({
        original_volume: originalVolume,
        voiceover_volume: voiceoverVolume,
        use_custom_music: useCustomMusic,
        add_subtitles: addSubtitles,
        subtitle_style: subtitleStyle || undefined,
      });
      if (response.mixed_videos) {
        setMixedVideos(response.mixed_videos);
        setAvailableSubtitleStyles(response.subtitle_styles || []);
        if (response.default_subtitle_style) {
          setSubtitleStyle(response.default_subtitle_style);
        }
        showToast('success', 'Mix ready. Download your renders below.');
      } else {
        showToast('error', 'Mixing failed', response.error);
      }
    } catch (error) {
      showToast('error', 'Mixing failed', (error as Error).message);
    } finally {
      setMixing(false);
      setLoadingMessage(null);
    }
  };

  const curatedVoices = useMemo(() => {
    return CURATED_VOICE_IDS.map((id) => {
      const fromApi = availableVoices.find((voice) => voice.id === id);
      return fromApi ?? CURATED_FALLBACKS[id];
    }).filter((voice): voice is ElevenLabsVoice => Boolean(voice));
  }, [availableVoices]);

  const otherVoices = useMemo(() => {
    const filtered = availableVoices.filter((voice) => !CURATED_VOICE_IDS.includes(voice.id));
    return [...filtered].sort((a, b) => a.name.localeCompare(b.name));
  }, [availableVoices]);

  const voiceOptions = useMemo(
    () => (showAllVoices ? [...curatedVoices, ...otherVoices] : curatedVoices),
    [curatedVoices, otherVoices, showAllVoices],
  );

  const selectedVoice = useMemo(() => {
    return voiceOptions.find((voice) => voice.id === voiceId) ?? CURATED_FALLBACKS[voiceId] ?? null;
  }, [voiceOptions, voiceId]);

  const selectedLanguageBadges = useMemo(
    () =>
      selectedLanguages.map((code) => (
        <Tag key={code} size="md" colorScheme="purple">
          <TagLabel>{languageName(code)}</TagLabel>
          <TagCloseButton onClick={() => toggleLanguage(code)} />
        </Tag>
      )),
    [selectedLanguages],
  );

  const languageCards = useMemo(
    () =>
      LANGUAGES.map((lang) => {
        const isSelected = selectedLanguages.includes(lang.code);
        return (
          <Card
            key={lang.code}
            borderWidth={1}
            borderColor={isSelected ? 'purple.400' : 'transparent'}
            bg={isSelected ? subtleBg : cardBg}
            cursor="pointer"
            onClick={() => toggleLanguage(lang.code)}
            transition="all 0.2s"
            _hover={{ borderColor: 'purple.300' }}
          >
            <CardBody>
              <Heading size="sm">{lang.name}</Heading>
              <Text fontSize="sm" color={helperTextColor}>
                {lang.code.toUpperCase()}
              </Text>
            </CardBody>
          </Card>
        );
      }),
    [cardBg, subtleBg, selectedLanguages],
  );

  const audioEntries = Object.entries(audioFiles);
  const mixedEntries = Object.entries(mixedVideos || {});

  return (
    <Container maxW="7xl" py={10} px={{ base: 4, md: 6 }}>
      <Stack spacing={12}>
        <Box bgGradient={heroGradient} borderRadius="2xl" color="white" p={{ base: 6, md: 10 }} shadow="xl">
          <Stack spacing={6} maxW="3xl">
            <Heading size="lg">AdLocalizer</Heading>
            <Text fontSize={{ base: 'md', md: 'lg' }} color="whiteAlpha.900">
              Transcribe, translate, generate voiceovers, and remaster videos with localized audio — all from the new React
              console.
            </Text>
            <Divider borderColor="whiteAlpha.400" />
            <HStack spacing={4} wrap="wrap">
              {HERO_STATS.map((stat) => (
                <Box
                  key={stat.label}
                  bg="whiteAlpha.200"
                  borderRadius="lg"
                  px={4}
                  py={3}
                  borderWidth="1px"
                  borderColor="whiteAlpha.300"
                >
                  <Text fontSize="sm" textTransform="uppercase" letterSpacing="wider" color="whiteAlpha.800">
                    {stat.label}
                  </Text>
                  <Text fontWeight="bold" fontSize="lg">
                    {stat.value}
                  </Text>
                </Box>
              ))}
            </HStack>
          </Stack>
        </Box>

        {loadingMessage && (
          <Alert status="info" borderRadius="md">
            <AlertIcon />
            <AlertDescription display="flex" alignItems="center">
              <Spinner size="sm" mr={3} />
              {loadingMessage}
            </AlertDescription>
          </Alert>
        )}

        <SimpleGrid columns={{ base: 1, md: 2 }} spacing={10}>
          <Card bg={cardBg} shadow="lg" borderRadius="2xl">
            <CardHeader>
              <Heading size="md">1. Transcribe media (optional)</Heading>
              <Text color={secondaryTextColor} fontSize="sm" mt={2}>
                Upload video or audio to auto-fill the text field. Supported: MP4, MOV, MP3, WAV, M4A …
              </Text>
            </CardHeader>
            <CardBody>
              <Stack spacing={4}>
                <FileDropZone
                  accept="video/*,audio/*"
                  icon={FiUploadCloud}
                  description={transcriptionFile ? transcriptionFile.name : 'Drop file or click to browse'}
                  helper="Video: MP4, MOV, WEBM | Audio: MP3, WAV, M4A, AAC, OGG, FLAC"
                  multiple={false}
                  onFilesSelected={(files) => {
                    const file = files.item(0);
                    if (file) setTranscriptionFile(file);
                  }}
                />
                <HStack spacing={3}>
                  <Button
                    colorScheme="purple"
                    onClick={handleTranscribe}
                    isLoading={transcriptionLoading}
                    leftIcon={<Icon as={FiUploadCloud} />}
                  >
                    Transcribe media
                  </Button>
                  <Button
                    variant="ghost"
                    leftIcon={<Icon as={FiTrash2} />}
                    onClick={() => {
                      setTranscriptionFile(null);
                      setTranscriptionText('');
                      setTextInput('');
                    }}
                  >
                    Clear
                  </Button>
                </HStack>
                {transcriptionText && (
                  <Alert status="success" borderRadius="md">
                    <AlertIcon />
                    <Box>
                      <AlertTitle>Transcription ready</AlertTitle>
                      <AlertDescription fontSize="sm">We pre-filled the text area below.</AlertDescription>
                    </Box>
                  </Alert>
                )}
              </Stack>
            </CardBody>
          </Card>

          <Card bg={cardBg} shadow="lg" borderRadius="2xl">
            <CardHeader>
              <Heading size="md">2. Text to translate</Heading>
              <Text color={secondaryTextColor} fontSize="sm" mt={2}>
                Paste copy or edit the transcription before generating localized variations.
              </Text>
            </CardHeader>
            <CardBody>
              <Textarea
                value={textInput}
                onChange={(event) => setTextInput(event.target.value)}
                minH="180px"
                placeholder="Photoroom is the best app in the world."
              />
            </CardBody>
          </Card>
        </SimpleGrid>

        <Card bg={cardBg} shadow="lg" borderRadius="2xl">
          <CardHeader>
              <Heading size="md">3. Choose languages</Heading>
              <Text color={secondaryTextColor} fontSize="sm" mt={2}>
                Select markets to localize. Use presets for the most common combinations.
              </Text>
          </CardHeader>
          <CardBody>
            <Stack spacing={6}>
              <HStack spacing={3} flexWrap="wrap">
                <Button size="sm" colorScheme="purple" fontWeight="600" onClick={selectTop5}>
                  Top 5 locales
                </Button>
                <Button
                  size="sm"
                  colorScheme="purple"
                  variant="outline"
                  fontWeight="600"
                  onClick={selectAllLanguages}
                >
                  Select all
                </Button>
                <Button
                  size="sm"
                  colorScheme="purple"
                  variant="ghost"
                  fontWeight="600"
                  onClick={clearLanguages}
                >
                  Clear all
                </Button>
              </HStack>
              <HStack spacing={2} wrap="wrap">
                {selectedLanguageBadges.length ? selectedLanguageBadges : (
                  <Text fontSize="sm" color="whiteAlpha.700">
                    No languages selected yet.
                  </Text>
                )}
              </HStack>
              <SimpleGrid columns={{ base: 1, md: 3, xl: 4 }} spacing={4}>
                {languageCards}
              </SimpleGrid>
            </Stack>
          </CardBody>
        </Card>

        <Card bg={cardBg} shadow="lg" borderRadius="2xl">
          <CardHeader>
              <Heading size="md">4. Translation mode</Heading>
              <Text color={secondaryTextColor} fontSize="sm" mt={2}>
                Choose tone before generating localized copy.
              </Text>
          </CardHeader>
          <CardBody>
            <RadioGroup value={translationMode} onChange={(value) => setTranslationMode(value as 'faithful' | 'creative')}>
              <HStack spacing={8} flexWrap="wrap">
                <Radio value="faithful">Faithful (literal)</Radio>
                <Radio value="creative">Creative (localized)</Radio>
              </HStack>
            </RadioGroup>
            <Button
              mt={6}
              colorScheme="purple"
              onClick={handleTranslate}
              isLoading={translateLoading}
              leftIcon={<Icon as={FiRefreshCcw} />}
            >
              Translate text
            </Button>
            {Object.keys(translations).length > 0 && (
              <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4} mt={6}>
                {Object.entries(translations).map(([code, value]) => (
                  <Card key={code} borderLeftWidth={4} borderColor="purple.400">
                    <CardBody>
                      <Heading size="sm" mb={3}>
                        {languageName(code)} ({code})
                      </Heading>
                      <Text fontSize="sm" color="gray.700">
                        {value}
                      </Text>
                    </CardBody>
                  </Card>
                ))}
              </SimpleGrid>
            )}
          </CardBody>
        </Card>

        <Card bg={cardBg} shadow="lg" borderRadius="2xl">
          <CardHeader>
              <Heading size="md">5. Generate voiceovers</Heading>
              <Text color={secondaryTextColor} fontSize="sm" mt={2}>
                Select a voice and AI model to synthesize localized audio.
              </Text>
          </CardHeader>
          <CardBody>
            <Stack spacing={6}>
              <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)' }} gap={4}>
                <GridItem>
                  <FormControl isDisabled={voicesLoading || voiceOptions.length === 0}>
                    <FormLabel>Voice</FormLabel>
                    <Select
                      placeholder={voicesLoading ? 'Loading voices…' : 'Select a voice'}
                      value={voiceId}
                      onChange={(event) => setVoiceId(event.target.value)}
                    >
                      {voiceOptions.map((voice) => (
                        <option key={voice.id} value={voice.id}>
                          {voice.name}
                        </option>
                      ))}
                    </Select>
                    {voicesError ? (
                      <FormHelperText color="red.400">{voicesError}</FormHelperText>
                    ) : (
                      <FormHelperText color={helperTextColor}>
                        Pulls automatically from your ElevenLabs dashboard (preview available when provided).
                      </FormHelperText>
                    )}
                  </FormControl>
                  {otherVoices.length > 0 && (
                    <Button
                      size="xs"
                      mt={2}
                      px={4}
                      borderRadius="full"
                      fontWeight="600"
                      bg={showAllVoices ? 'transparent' : 'purple.500'}
                      color={showAllVoices ? featuredToggleText : 'white'}
                      borderWidth="1px"
                      borderColor="purple.400"
                      _hover={{ bg: showAllVoices ? featuredToggleHover : 'purple.400' }}
                      onClick={() => setShowAllVoices((prev) => !prev)}
                      isDisabled={voicesLoading}
                    >
                      {showAllVoices ? 'Show featured voices only' : `Load ${otherVoices.length} more voices`}
                    </Button>
                  )}
                  {selectedVoice?.preview_url && (
                    <Box mt={4}>
                      <HStack justify="space-between" mb={2}>
                        <Text fontSize="sm" color={secondaryTextColor}>
                          Voice preview
                        </Text>
                        <Button
                          size="xs"
                          variant="ghost"
                          leftIcon={<Icon as={FiPlay} />}
                          onClick={() => {
                            const audio = new Audio(selectedVoice.preview_url);
                            void audio.play();
                          }}
                        >
                          Tap to play
                        </Button>
                      </HStack>
                      <audio controls src={selectedVoice.preview_url} style={{ width: '100%' }} />
                    </Box>
                  )}
                </GridItem>
                <GridItem>
                  <FormControl>
                    <FormLabel>Voice model</FormLabel>
                    <Select value={voiceModel} onChange={(event) => setVoiceModel(event.target.value)}>
                      {VOICE_MODEL_OPTIONS.map((model) => (
                        <option key={model.value} value={model.value}>
                          {model.label}
                        </option>
                      ))}
                    </Select>
                    <FormHelperText color={helperTextColor}>
                      Select a model for vocal quality vs speed.
                    </FormHelperText>
                  </FormControl>
                </GridItem>
              </Grid>
              <Button
                onClick={handleGenerateVoiceovers}
                colorScheme="purple"
                leftIcon={<Icon as={FiMusic} />}
                isLoading={voiceLoading}
              >
                Generate voiceovers
              </Button>
              {audioEntries.length > 0 && (
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                  {audioEntries.map(([code, path]) => {
                    const filename = path.split('/').pop() ?? '';
                    const audioUrl = resolveApiUrl(`/audio/${encodeURIComponent(filename)}`);
                    return (
                      <Card key={code} borderLeftWidth={4} borderColor="green.400">
                        <CardBody>
                          <Heading size="sm" mb={3}>
                            {languageName(code)} ({code})
                          </Heading>
                          <audio controls style={{ width: '100%' }} src={audioUrl} />
                          <Button
                            mt={3}
                            size="sm"
                            as="a"
                            href={audioUrl}
                            download={filename}
                            leftIcon={<Icon as={FiDownload} />}
                          >
                            Download
                          </Button>
                        </CardBody>
                      </Card>
                    );
                  })}
                </SimpleGrid>
              )}
            </Stack>
          </CardBody>
        </Card>

        <Card bg={cardBg} shadow="lg" borderRadius="2xl">
          <CardHeader>
            <Heading size="md">6. Mix with video</Heading>
            <Text color={secondaryTextColor} fontSize="sm" mt={2}>
              Upload your video, adjust volumes, and optionally add custom music or subtitles.
            </Text>
          </CardHeader>
          <CardBody>
            <Stack spacing={6}>
              <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                <Stack spacing={4}>
                  <FileDropZone
                    icon={FiVideo}
                    description={videoFile ? videoFile.name : 'Upload localized video base'}
                    helper="Supported: MP4, MOV"
                    accept="video/*"
                    multiple={false}
                    onFilesSelected={(files) => {
                      const file = files.item(0);
                      if (file) handleVideoUpload(file);
                    }}
                  />
                  {videoInfo && (
                    <Alert status="success" borderRadius="md">
                      <AlertIcon />
                      <Box>
                        <AlertTitle>{videoInfo.filename}</AlertTitle>
                        <AlertDescription fontSize="sm">
                          {formatFileSize(videoInfo.size)} ready for remix.
                        </AlertDescription>
                      </Box>
                    </Alert>
                  )}
                  <Stack spacing={3}>
                    <Heading size="sm">Volume controls</Heading>
                    <Box>
                      <FormLabel color={secondaryTextColor} fontSize="sm">
                        Original video volume ({Math.round(originalVolume * 100)}%)
                      </FormLabel>
                      <Slider value={originalVolume} min={0} max={1} step={0.05} onChange={setOriginalVolume}>
                        <SliderTrack>
                          <SliderFilledTrack />
                        </SliderTrack>
                        <SliderThumb />
                      </Slider>
                    </Box>
                    <Box>
                      <FormLabel color={secondaryTextColor} fontSize="sm">
                        Voiceover volume ({Math.round(voiceoverVolume * 100)}%)
                      </FormLabel>
                      <Slider value={voiceoverVolume} min={0} max={1.5} step={0.05} onChange={setVoiceoverVolume}>
                        <SliderTrack>
                          <SliderFilledTrack />
                        </SliderTrack>
                        <SliderThumb />
                      </Slider>
                    </Box>
                  </Stack>
                </Stack>
                <Stack spacing={4}>
                  <Tabs variant="soft-rounded" colorScheme="purple">
                    <TabList>
                      <Tab>Music</Tab>
                      <Tab>Subtitles</Tab>
                    </TabList>
                    <TabPanels>
                      <TabPanel>
                        <Stack spacing={3}>
                          <Heading size="sm">Add music overlay</Heading>
                          <Switch
                            isChecked={useCustomMusic}
                            onChange={(event) => setUseCustomMusic(event.target.checked)}
                          >
                            {useCustomMusic ? 'Using custom music' : 'Enable custom or default music'}
                          </Switch>
                          {useCustomMusic && (
                            <Stack spacing={3}>
                              <FileDropZone
                                icon={FiMusic}
                                description={customMusicFile ? customMusicFile.name : 'Upload custom music'}
                                helper="Supported audio formats: MP3, WAV, M4A, AAC"
                                accept="audio/*"
                                multiple={false}
                                onFilesSelected={(files) => {
                                  const file = files.item(0);
                                  if (file) handleMusicUpload(file);
                                }}
                              />
                              <FormControl>
                                <FormLabel color={secondaryTextColor}>Or choose a default track</FormLabel>
                                <Select
                                  value={defaultMusicFile}
                                  onChange={(event) => handleSelectDefaultMusic(event.target.value)}
                                >
                                  <option value="">Select...</option>
                                  {DEFAULT_MUSIC_OPTIONS.map((option) => (
                                    <option key={option.file} value={option.file}>
                                      {option.label}
                                    </option>
                                  ))}
                                </Select>
                              </FormControl>
                            </Stack>
                          )}
                        </Stack>
                      </TabPanel>
                      <TabPanel>
                        <Stack spacing={3}>
                          <Switch isChecked={addSubtitles} onChange={(event) => setAddSubtitles(event.target.checked)}>
                            Burn subtitles into video
                          </Switch>
                          {addSubtitles && availableSubtitleStyles.length > 0 && (
                            <FormControl>
                              <FormLabel>Subtitle style</FormLabel>
                              <Select value={subtitleStyle} onChange={(event) => setSubtitleStyle(event.target.value)}>
                                {availableSubtitleStyles.map((style) => (
                                  <option key={style} value={style}>
                                    {style}
                                  </option>
                                ))}
                              </Select>
                            </FormControl>
                          )}
                        </Stack>
                      </TabPanel>
                    </TabPanels>
                  </Tabs>
                </Stack>
              </SimpleGrid>
              <Button
                colorScheme="purple"
                leftIcon={<Icon as={FiRefreshCcw} />}
                onClick={handleMixAudio}
                isLoading={mixing}
              >
                Mix audio & render videos
              </Button>
              {mixedEntries.length > 0 && (
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                  {mixedEntries.map(([code, value]) => {
                    if (code === 'custom_music' && typeof value === 'string') {
                      const filename = value.split('/').pop() ?? value;
                      const downloadUrl = resolveApiUrl(`/adlocalizer/download/${encodeURIComponent(filename)}`);
                      return (
                        <Card key={code} borderLeftWidth={4} borderColor="blue.400">
                          <CardBody>
                            <Heading size="sm" mb={2}>
                              Custom music mix
                            </Heading>
                            <Text fontSize="sm" color={helperTextColor} mb={2}>
                              Video rendered with music only
                            </Text>
                            <Button
                              as="a"
                              href={downloadUrl}
                              leftIcon={<Icon as={FiDownload} />}
                              size="sm"
                            >
                              Download
                            </Button>
                          </CardBody>
                        </Card>
                      );
                    }

                    const entry = typeof value === 'string' ? { clean: value } : (value || {});
                    const cleanFile = entry.clean?.split('/').pop();
                    const subtitleFile = entry.subtitled?.split('/').pop();
                    const cleanDownloadUrl = cleanFile
                      ? resolveApiUrl(`/adlocalizer/download/${encodeURIComponent(cleanFile)}`)
                      : null;
                    const subtitleDownloadUrl = subtitleFile
                      ? resolveApiUrl(`/adlocalizer/download/${encodeURIComponent(subtitleFile)}`)
                      : null;
                    return (
                      <Card key={code} borderLeftWidth={4} borderColor="teal.400">
                        <CardBody>
                          <Heading size="sm" mb={2}>
                            {languageName(code)} ({code})
                          </Heading>
                          <Stack spacing={2} direction={{ base: 'column', sm: 'row' }}>
                            {cleanFile && cleanDownloadUrl && (
                              <Button
                                size="sm"
                                variant="outline"
                                as="a"
                                href={cleanDownloadUrl}
                                leftIcon={<Icon as={FiDownload} />}
                              >
                                Download clean
                              </Button>
                            )}
                            {subtitleFile && subtitleDownloadUrl && (
                              <Button
                                size="sm"
                                colorScheme="purple"
                                as="a"
                                href={subtitleDownloadUrl}
                                leftIcon={<Icon as={FiDownload} />}
                              >
                                Download subtitles
                              </Button>
                            )}
                          </Stack>
                        </CardBody>
                      </Card>
                    );
                  })}
                </SimpleGrid>
              )}
            </Stack>
          </CardBody>
        </Card>

        <HStack spacing={4} wrap="wrap" justify="space-between">
          <Button
            as="a"
            href={resolveApiUrl('/api/download-all-voiceovers')}
            variant="outline"
            leftIcon={<Icon as={FiDownload} />}
          >
            Download all voiceovers
          </Button>
          <Button
            as="a"
            href={resolveApiUrl('/api/download-all')}
            variant="outline"
            leftIcon={<Icon as={FiDownload} />}
          >
            Download all videos
          </Button>
        </HStack>
      </Stack>
    </Container>
  );
};

export default AdLocalizerPage;
