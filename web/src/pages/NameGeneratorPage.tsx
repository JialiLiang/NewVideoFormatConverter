import {
  Alert,
  AlertDescription,
  AlertIcon,
  AlertTitle,
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
  Container,
  Divider,
  FormControl,
  FormLabel,
  Grid,
  GridItem,
  Heading,
  HStack,
  Input,
  NumberInput,
  NumberInputField,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  useColorModeValue,
  useToast,
  Wrap,
  WrapItem,
} from '@chakra-ui/react';
import { useMemo, useState } from 'react';
import { apiClient } from '../api/client';
import {
  buildCreativeName,
  creatorTypeOptions,
  defaultCreativeState,
  dimensionOptions,
  featureOptions,
  formatToPascalCase,
  generateIterationName,
  hookOptions,
  languageOptions,
  musicOptions,
  TODAY_YYYYMMDD,
  validateCreativeName,
  voiceOptions,
} from '../utils/nameGenerator';
import type { CreativeNameFormState, NameValidationResult } from '../utils/nameGenerator';

const copyToClipboard = async (value: string, toast: ReturnType<typeof useToast>) => {
  try {
    await navigator.clipboard.writeText(value);
    toast({
      status: 'success',
      title: 'Copied to clipboard',
      duration: 1500,
      isClosable: true,
    });
  } catch (error) {
    toast({ status: 'error', title: 'Unable to copy', description: String(error) });
  }
};

const ResultList = ({ title, results }: { title: string; results: NameValidationResult['structureChecks'] }) => (
  <Box>
    <Heading size="sm" mb={3}>
      {title}
    </Heading>
    <Stack spacing={2}>
      {results.map((item) => (
        <HStack key={`${item.label}-${item.value}`} spacing={3} align="flex-start">
          <Badge colorScheme={item.isValid ? 'green' : 'red'}>{item.isValid ? 'OK' : 'Check'}</Badge>
          <Box>
            <Text fontWeight="medium">{item.label}</Text>
            <Text fontSize="sm" color="gray.600">
              {item.value}
            </Text>
          </Box>
        </HStack>
      ))}
    </Stack>
  </Box>
);

export const NameGeneratorPage = () => {
  const [form, setForm] = useState<CreativeNameFormState>(defaultCreativeState);
  const [iterationSource, setIterationSource] = useState('');
  const [iterationNumber, setIterationNumber] = useState(1);
  const [nameToValidate, setNameToValidate] = useState('');
  const [isCorrecting, setIsCorrecting] = useState(false);
  const [correctedName, setCorrectedName] = useState<{ corrected: string; reasoning: string } | null>(null);
  const toast = useToast();
  const heroGradient = useColorModeValue(
    'linear(to-r, purple.500, pink.500)',
    'linear(to-r, rgba(112,76,255,0.7), rgba(236,72,153,0.5))',
  );
  const cardBg = useColorModeValue('white', 'rgba(19,18,40,0.85)');
  const subtleBg = useColorModeValue('purple.50', 'rgba(112,76,255,0.18)');
  const iterationBg = useColorModeValue('green.50', 'rgba(16,185,129,0.16)');

  const preview = useMemo(() => buildCreativeName(form), [form]);
  const iterationResult = useMemo(
    () => generateIterationName(iterationSource, iterationNumber) ?? '',
    [iterationSource, iterationNumber],
  );
  const iterationUploadPreview = useMemo(
    () => (iterationResult ? `12345_Jiali_${iterationResult}_${TODAY_YYYYMMDD}` : ''),
    [iterationResult],
  );
  const validation = useMemo(() => (nameToValidate ? validateCreativeName(nameToValidate) : null), [nameToValidate]);

  const updateForm = <K extends keyof CreativeNameFormState>(key: K, value: CreativeNameFormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleCreatorNameChange = (value: string) => {
    updateForm('creatorName', formatToPascalCase(value));
  };

  const handleFilenameChange = (value: string) => {
    updateForm('filename', value);
  };

  const handleHookChange = (value: CreativeNameFormState['hook']) => {
    updateForm('hook', value);
    if (value !== 'text') updateForm('hookText', '');
    if (value !== 'UGC') updateForm('hookUgc', '');
    if (value !== 'custom') updateForm('hookCustom', '');
  };

  const handleVoiceChange = (value: CreativeNameFormState['voiceOver']) => {
    updateForm('voiceOver', value);
    if (value !== 'custom') updateForm('voiceName', '');
  };

  const handleMusicChange = (value: CreativeNameFormState['music']) => {
    updateForm('music', value);
    if (value !== 'custom') updateForm('musicCustom', '');
  };

  const runCorrection = async () => {
    if (!nameToValidate.trim()) return;
    setIsCorrecting(true);
    setCorrectedName(null);
    try {
      const response = await apiClient.post<{ corrected: string; reasoning: string }>(
        '/api/correct-creative-name',
        { name: nameToValidate.trim() },
      );
      setCorrectedName(response.data);
      toast({ status: 'success', title: 'Name corrected' });
    } catch (error) {
      toast({ status: 'error', title: 'Unable to correct creative name' });
    } finally {
      setIsCorrecting(false);
    }
  };

  const clearForm = () => {
    setForm(defaultCreativeState);
    setCorrectedName(null);
  };

  return (
    <Container maxW="7xl" py={10} px={{ base: 4, md: 6 }}>
      <Stack spacing={12}>
        <Box bgGradient={heroGradient} borderRadius="2xl" color="white" p={{ base: 6, md: 10 }} shadow="xl">
          <Stack spacing={5} maxW="3xl">
            <Heading size="lg">Creative Name Generator</Heading>
            <Text fontSize={{ base: 'md', md: 'lg' }} color="whiteAlpha.900">
              Build AdManage-ready filenames with live preview, iteration helpers, and validation directly in the React shell.
            </Text>
            <Divider borderColor="whiteAlpha.400" />
            <Wrap spacing={4}>
              <WrapItem>
                <StatBox label="Formats" value="AdManage / Basic" />
              </WrapItem>
              <WrapItem>
                <StatBox label="Hooks" value="8 presets" />
              </WrapItem>
              <WrapItem>
                <StatBox label="Locales" value="18 languages" />
              </WrapItem>
            </Wrap>
          </Stack>
        </Box>

        <SimpleGrid columns={{ base: 1, xl: 2 }} spacing={10} alignItems="stretch">
          <Card bg={cardBg} shadow="lg" borderRadius="2xl">
            <CardHeader pb={0}>
              <Heading size="md">Creative inputs</Heading>
              <Text color="gray.500" fontSize="sm" mt={2}>
                Fill in metadata — fields auto-normalize to PascalCase and stay aligned with AdManage rules.
              </Text>
            </CardHeader>
            <CardBody>
              <Grid templateColumns={{ base: '1fr', md: 'repeat(2, 1fr)' }} gap={4}>
                <GridItem colSpan={{ base: 1, md: 1 }}>
                  <FormControl>
                    <FormLabel>Creator Type</FormLabel>
                    <Select
                      value={form.creatorType}
                      onChange={(event) => updateForm('creatorType', event.target.value as CreativeNameFormState['creatorType'])}
                    >
                      {creatorTypeOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </Select>
                  </FormControl>
                </GridItem>
                <GridItem colSpan={{ base: 1, md: 1 }}>
                  {form.creatorType !== 'internal' && (
                    <FormControl>
                      <FormLabel>Creator Name</FormLabel>
                      <Input value={form.creatorName} onChange={(event) => handleCreatorNameChange(event.target.value)} />
                    </FormControl>
                  )}
                </GridItem>

                <GridItem colSpan={{ base: 1, md: 2 }}>
                  <FormControl>
                    <FormLabel>Creative Name</FormLabel>
                    <Input value={form.filename} onChange={(event) => handleFilenameChange(event.target.value)} />
                  </FormControl>
                </GridItem>

                <GridItem colSpan={{ base: 1, md: 1 }}>
                  <FormControl>
                    <FormLabel>Creative #</FormLabel>
                    <NumberInput
                      value={form.creativeNumber}
                      min={1}
                      max={999}
                      onChange={(_, valueAsNumber) => updateForm('creativeNumber', valueAsNumber || 1)}
                    >
                      <NumberInputField />
                    </NumberInput>
                  </FormControl>
                </GridItem>

                <GridItem colSpan={{ base: 1, md: 1 }}>
                  <FormControl>
                    <FormLabel>Language</FormLabel>
                    <Select value={form.language} onChange={(event) => updateForm('language', event.target.value)}>
                      {languageOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </Select>
                  </FormControl>
                </GridItem>

                <GridItem colSpan={{ base: 1, md: 1 }}>
                  <FormControl>
                    <FormLabel>Dimension</FormLabel>
                    <Select
                      value={form.dimension}
                      onChange={(event) => updateForm('dimension', event.target.value as CreativeNameFormState['dimension'])}
                    >
                      {dimensionOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </Select>
                  </FormControl>
                </GridItem>

                <GridItem colSpan={{ base: 1, md: 1 }}>
                  <FormControl>
                    <FormLabel>Feature</FormLabel>
                    <Wrap spacing={2}>
                      {featureOptions.map((feature) => (
                        <WrapItem key={feature}>
                          <Button
                            variant={form.feature === feature ? 'solid' : 'outline'}
                            colorScheme="purple"
                            size="sm"
                            onClick={() => updateForm('feature', feature)}
                          >
                            {feature}
                          </Button>
                        </WrapItem>
                      ))}
                    </Wrap>
                  </FormControl>
                </GridItem>

                <GridItem colSpan={{ base: 1, md: 1 }}>
                  <FormControl>
                    <FormLabel>Hook</FormLabel>
                    <Select
                      value={form.hook}
                      onChange={(event) => handleHookChange(event.target.value as CreativeNameFormState['hook'])}
                    >
                      {hookOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </Select>
                  </FormControl>
                </GridItem>

                {form.hook === 'text' && (
                  <GridItem colSpan={{ base: 1, md: 1 }}>
                    <FormControl>
                      <FormLabel>Hook Script</FormLabel>
                      <Input
                        value={form.hookText ?? ''}
                        onChange={(event) => updateForm('hookText', formatToPascalCase(event.target.value))}
                      />
                    </FormControl>
                  </GridItem>
                )}

                {form.hook === 'UGC' && (
                  <GridItem colSpan={{ base: 1, md: 1 }}>
                    <FormControl>
                      <FormLabel>UGC Handle</FormLabel>
                      <Input
                        value={form.hookUgc ?? ''}
                        onChange={(event) => updateForm('hookUgc', event.target.value.trim())}
                      />
                    </FormControl>
                  </GridItem>
                )}

                {form.hook === 'custom' && (
                  <GridItem colSpan={{ base: 1, md: 1 }}>
                    <FormControl>
                      <FormLabel>Custom Hook</FormLabel>
                      <Input
                        value={form.hookCustom ?? ''}
                        onChange={(event) => updateForm('hookCustom', formatToPascalCase(event.target.value))}
                      />
                    </FormControl>
                  </GridItem>
                )}

                <GridItem colSpan={{ base: 1, md: 1 }}>
                  <FormControl>
                    <FormLabel>Voice Over</FormLabel>
                    <Select
                      value={form.voiceOver}
                      onChange={(event) => handleVoiceChange(event.target.value as CreativeNameFormState['voiceOver'])}
                    >
                      {voiceOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </Select>
                  </FormControl>
                </GridItem>

                {form.voiceOver === 'custom' && (
                  <GridItem colSpan={{ base: 1, md: 1 }}>
                    <FormControl>
                      <FormLabel>Voice Name</FormLabel>
                      <Input
                        value={form.voiceName ?? ''}
                        onChange={(event) => updateForm('voiceName', formatToPascalCase(event.target.value))}
                      />
                    </FormControl>
                  </GridItem>
                )}

                {form.voiceOver !== 'null' && (
                  <GridItem colSpan={{ base: 1, md: 2 }}>
                    <FormControl>
                      <FormLabel>Voice Script</FormLabel>
                      <Input
                        value={form.voScript ?? ''}
                        onChange={(event) => updateForm('voScript', formatToPascalCase(event.target.value))}
                      />
                    </FormControl>
                  </GridItem>
                )}

                <GridItem colSpan={{ base: 1, md: 1 }}>
                  <FormControl>
                    <FormLabel>Music</FormLabel>
                    <Select
                      value={form.music}
                      onChange={(event) => handleMusicChange(event.target.value as CreativeNameFormState['music'])}
                    >
                      {musicOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </Select>
                  </FormControl>
                </GridItem>

                {form.music === 'custom' && (
                  <GridItem colSpan={{ base: 1, md: 1 }}>
                    <FormControl>
                      <FormLabel>Song Name</FormLabel>
                      <Input
                        value={form.musicCustom ?? ''}
                        onChange={(event) => updateForm('musicCustom', formatToPascalCase(event.target.value))}
                      />
                    </FormControl>
                  </GridItem>
                )}
              </Grid>

              <HStack spacing={4} mt={6}>
                <Button colorScheme="purple" onClick={clearForm}>
                  Reset form
                </Button>
              </HStack>
            </CardBody>
          </Card>

          <Stack spacing={6}>
            <Card bg={cardBg} shadow="lg" borderRadius="2xl">
              <CardHeader pb={0}>
                <Heading size="sm">Live creative name</Heading>
                <Text color="gray.500" fontSize="sm" mt={2}>
                  Preview updates automatically while you type.
                </Text>
              </CardHeader>
              <CardBody>
                <Stack spacing={4}>
                  <Box
                    bg={subtleBg}
                    borderRadius="xl"
                    p={4}
                    borderWidth="1px"
                    borderColor="purple.200"
                    fontFamily="mono"
                    fontWeight="semibold"
                    wordBreak="break-all"
                  >
                    {preview.preview}
                  </Box>
                  <HStack spacing={3}>
                    <Button size="sm" colorScheme="purple" onClick={() => copyToClipboard(preview.preview, toast)}>
                      Copy name
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      colorScheme="purple"
                      onClick={() => copyToClipboard(preview.sampleWithId, toast)}
                    >
                      Copy sample (with ID)
                    </Button>
                  </HStack>
                </Stack>
              </CardBody>
            </Card>

            <Card bg={cardBg} shadow="lg" borderRadius="2xl">
              <CardHeader pb={0}>
                <Heading size="sm">Sample AdManage output</Heading>
                <Text color="gray.500" fontSize="sm" mt={2}>
                  Includes reference ID and date for tracker copy/paste.
                </Text>
              </CardHeader>
              <CardBody>
                <Text fontFamily="mono" wordBreak="break-all">
                  {preview.sampleWithId}
                </Text>
              </CardBody>
            </Card>
          </Stack>
        </SimpleGrid>

        <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={10}>
          <Card bg={cardBg} shadow="lg" borderRadius="2xl">
            <CardHeader pb={0}>
              <Heading size="md">Iteration helper</Heading>
              <Text color="gray.500" fontSize="sm" mt={2}>
                Paste an existing AdManage filename to auto-generate the next iteration suffix.
              </Text>
            </CardHeader>
            <CardBody>
              <Stack spacing={4}>
                <FormControl>
                  <FormLabel>Existing AdManage filename</FormLabel>
                  <Textarea
                    value={iterationSource}
                    onChange={(event) => setIterationSource(event.target.value)}
                    placeholder="e.g. 10044_Houda_freelancer-Jeremy_Clothes_HOOK-any_VO-Tom_MUSIC-any_PO_[IMGT-MODEL]_[en]"
                  />
                </FormControl>
                <FormControl maxW="200px">
                  <FormLabel>Iteration number</FormLabel>
                  <NumberInput value={iterationNumber} min={1} max={99} onChange={(_, value) => setIterationNumber(value || 1)}>
                    <NumberInputField />
                  </NumberInput>
                </FormControl>
                <Text fontSize="sm" color="gray.500">
                  Output keeps only the creative filename and tags. AdManage will add ID, owner, and date when you
                  import it back.
                </Text>
                <Box
                  bgGradient="linear(to-r, purple.500, purple.600)"
                  borderRadius="2xl"
                  p={6}
                  color="white"
                  boxShadow="xl"
                >
                  <Text fontFamily="mono" fontWeight="semibold" wordBreak="break-all" mb={4}>
                    {iterationResult || 'internal_[filename]-ITE-1_HOOK-any_VO-any_MUSIC-any_PO_[AIBG]_[en]'}
                  </Text>
                  <Button
                    size="sm"
                    bg="whiteAlpha.300"
                    _hover={{ bg: 'whiteAlpha.400' }}
                    onClick={() => iterationResult && copyToClipboard(iterationResult, toast)}
                    isDisabled={!iterationResult}
                  >
                    Copy iteration
                  </Button>
                  <Box bg="whiteAlpha.200" borderRadius="xl" p={4} mt={5}>
                    <HStack spacing={2} mb={2} color="whiteAlpha.900" fontWeight="semibold" fontSize="sm">
                      <i className="fas fa-info-circle" />
                      <Text>Preview after upload</Text>
                    </HStack>
                    <Text fontFamily="mono" fontSize="sm" wordBreak="break-all">
                      {iterationUploadPreview || '12345_Jiali_internal_[filename]-ITE-1_HOOK-any_VO-any_MUSIC-any_PO_[AIBG]_[en]_01012025'}
                    </Text>
                  </Box>
                </Box>
              </Stack>
            </CardBody>
          </Card>

          <Card bg={cardBg} shadow="lg" borderRadius="2xl">
            <CardHeader pb={0}>
              <Heading size="md">Validator & fixer</Heading>
              <Text color="gray.500" fontSize="sm" mt={2}>
                Validate legacy names and call the AI corrector if structure drifts.
              </Text>
            </CardHeader>
            <CardBody>
              <Stack spacing={4}>
                <FormControl>
                  <FormLabel>Creative name to validate</FormLabel>
                  <Textarea
                    value={nameToValidate}
                    onChange={(event) => setNameToValidate(event.target.value)}
                    placeholder="Paste creative name..."
                  />
                </FormControl>
                <HStack spacing={3}>
                  <Button
                    colorScheme="purple"
                    onClick={runCorrection}
                    isLoading={isCorrecting}
                    isDisabled={!nameToValidate.trim()}
                  >
                    Correct with AI
                  </Button>
                  {validation && (
                    <Badge colorScheme={validation.isValid ? 'green' : 'orange'}>{
                      validation.isValid ? 'Looks good' : 'Needs attention'
                    }</Badge>
                  )}
                </HStack>

                {correctedName && (
                  <Alert status="success" borderRadius="md">
                    <AlertIcon />
                    <Box>
                      <AlertTitle>Suggested correction</AlertTitle>
                      <AlertDescription>
                        <Text fontFamily="mono" fontWeight="semibold">
                          {correctedName.corrected}
                        </Text>
                        <Text fontSize="sm" color="gray.600">
                          {correctedName.reasoning}
                        </Text>
                        <Button
                          size="sm"
                          mt={3}
                          onClick={() => copyToClipboard(correctedName.corrected, toast)}
                          colorScheme="purple"
                        >
                          Copy corrected name
                        </Button>
                      </AlertDescription>
                    </Box>
                  </Alert>
                )}

                {validation && (
                  <Alert status={validation.isValid ? 'success' : 'warning'} borderRadius="md">
                    <AlertIcon />
                    <Box>
                      <AlertTitle>{validation.isValid ? 'Valid format' : 'Check the structure'}</AlertTitle>
                      <AlertDescription>{validation.message}</AlertDescription>
                    </Box>
                  </Alert>
                )}

                {validation && (
                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                    <ResultList title="Structure" results={validation.structureChecks} />
                    <ResultList title="Content" results={validation.contentChecks} />
                  </SimpleGrid>
                )}
              </Stack>
            </CardBody>
          </Card>
        </SimpleGrid>
      </Stack>
    </Container>
  );
};

const StatBox = ({ label, value }: { label: string; value: string }) => (
  <Box bg="whiteAlpha.200" borderRadius="lg" px={4} py={3} borderWidth="1px" borderColor="whiteAlpha.300">
    <Text fontSize="sm" textTransform="uppercase" letterSpacing="wider" color="whiteAlpha.800">
      {label}
    </Text>
    <Text fontWeight="bold" fontSize="lg">
      {value}
    </Text>
  </Box>
);

export default NameGeneratorPage;
