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
  Flex,
  Heading,
  HStack,
  Icon,
  Progress,
  SimpleGrid,
  Stack,
  Tag,
  TagCloseButton,
  Text,
  useColorModeValue,
  useToast,
  Wrap,
  WrapItem,
} from '@chakra-ui/react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { FiFilm, FiTrash2, FiUploadCloud, FiDownload, FiStopCircle } from 'react-icons/fi';
import { FileDropZone } from '../components/FileDropZone';
import {
  cancelJob,
  fetchStatus,
  startConversion,
  type ConversionResult,
  type ConversionStatus,
  type VideoFormat,
} from '../api/videoConverter';
import { resolveApiUrl } from '../api/client';

const AVAILABLE_FORMATS: { id: VideoFormat; label: string; subtitle: string }[] = [
  { id: 'square', label: 'Square', subtitle: '1080 × 1080' },
  { id: 'square_blur', label: 'Square + Blur', subtitle: '1080 × 1080' },
  { id: 'landscape', label: 'Landscape + Blur', subtitle: '1920 × 1080' },
  { id: 'vertical', label: 'Vertical + Blur', subtitle: '1080 × 1920' },
];

const HERO_CARDS = [
  { label: 'Formats', value: '4 presets' },
  { label: 'Max size', value: '100 MB/file' },
  { label: 'Processing', value: '~5 min/video' },
];

const formatEta = (status?: ConversionStatus) => status?.estimated_time_remaining_human ?? '—';

export const VideoConverterPage = () => {
  const heroGradient = useColorModeValue(
    'linear(to-r, purple.500, blue.500)',
    'linear(to-r, rgba(112,76,255,0.65), rgba(59,130,246,0.5))',
  );
  const cardBg = useColorModeValue('white', 'rgba(19,18,40,0.85)');
  const subtleBg = useColorModeValue('purple.50', 'rgba(112,76,255,0.18)');
  const toast = useToast();

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [selectedFormats, setSelectedFormats] = useState<VideoFormat[]>(['square']);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<ConversionStatus | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);

  const progress = status?.progress ?? 0;
  const isProcessing = status?.status === 'processing' || status?.status === 'queued';
  const isCompleted = status?.status === 'completed';

  const handleFilesSelected = (files: FileList) => {
    const list = Array.from(files);
    const filtered = list.filter((file) => /\.(mp4|mov)$/i.test(file.name));
    if (filtered.length !== list.length) {
      toast({ status: 'warning', title: 'Unsupported file skipped', description: 'Only MP4 and MOV are accepted.' });
    }
    setSelectedFiles((prev) => [...prev, ...filtered]);
  };

  const removeFile = (fileName: string) => {
    setSelectedFiles((prev) => prev.filter((file) => file.name !== fileName));
  };

  const toggleFormat = (format: VideoFormat) => {
    setSelectedFormats((prev) =>
      prev.includes(format) ? prev.filter((item) => item !== format) : [...prev, format],
    );
  };

  const resetJob = useCallback(() => {
    setJobId(null);
    setStatus(null);
    setIsCancelling(false);
  }, []);

  const handleStart = async () => {
    if (selectedFiles.length === 0) {
      toast({ status: 'warning', title: 'Add videos first' });
      return;
    }
    if (selectedFormats.length === 0) {
      toast({ status: 'warning', title: 'Pick at least one output format' });
      return;
    }

    setIsSubmitting(true);
    resetJob();
    try {
      const response = await startConversion(selectedFiles, selectedFormats);
      setJobId(response.job_id);
      setStatus({ status: 'queued', progress: 0, results: [] });
      toast({ status: 'info', title: 'Processing started', description: 'We will update status automatically.' });
    } catch (error) {
      toast({ status: 'error', title: 'Upload failed', description: (error as Error).message });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = async () => {
    if (!jobId) return;
    setIsCancelling(true);
    try {
      await cancelJob(jobId);
      toast({ status: 'info', title: 'Cancellation requested' });
    } catch (error) {
      toast({ status: 'error', title: 'Unable to cancel', description: (error as Error).message });
    } finally {
      setIsCancelling(false);
    }
  };

  useEffect(() => {
    if (!jobId) return;

    let cancelled = false;

    const fetchAndUpdate = async () => {
      try {
        const nextStatus = await fetchStatus(jobId);
        if (!cancelled) {
          setStatus(nextStatus);
          if (nextStatus.status === 'completed' || nextStatus.status === 'error' || nextStatus.status === 'cancelled') {
            clearInterval(intervalId);
          }
        }
      } catch (error) {
        console.error('Status polling failed', error);
      }
    };

    fetchAndUpdate();
    const intervalId = window.setInterval(fetchAndUpdate, 2000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [jobId]);

  useEffect(() => () => resetJob(), [resetJob]);

  const results = status?.results ?? [];
  const errors = status?.errors ?? [];

  const heroCards = useMemo(
    () =>
      HERO_CARDS.map((card) => (
        <Box
          key={card.label}
          bg="whiteAlpha.200"
          borderRadius="lg"
          px={4}
          py={3}
          borderWidth="1px"
          borderColor="whiteAlpha.300"
        >
          <Text fontSize="sm" textTransform="uppercase" letterSpacing="wider" color="whiteAlpha.800">
            {card.label}
          </Text>
          <Text fontWeight="bold" fontSize="lg">
            {card.value}
          </Text>
        </Box>
      )),
    [],
  );

  return (
    <Container maxW="6xl" py={10} px={{ base: 4, md: 6 }}>
      <Stack spacing={10}>
        <Box bgGradient={heroGradient} borderRadius="2xl" color="white" p={{ base: 6, md: 10 }} shadow="xl">
          <Stack spacing={5} maxW="3xl">
            <Heading size="lg">Video Format Converter</Heading>
            <Text fontSize={{ base: 'md', md: 'lg' }} color="whiteAlpha.900">
              Upload a batch of creatives, select your target ratios, and let the renderer handle blurred fills and exports
              while you keep editing.
            </Text>
            <Divider borderColor="whiteAlpha.400" />
            <HStack spacing={4} wrap="wrap">
              {heroCards}
            </HStack>
          </Stack>
        </Box>

        <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={8}>
          <Card bg={cardBg} shadow="lg" borderRadius="2xl">
            <CardHeader>
              <Heading size="md">1. Upload videos</Heading>
              <Text color="gray.500" fontSize="sm" mt={2}>
                Drag up to 5 creatives (MP4 or MOV). Each file should be under 100 MB.
              </Text>
            </CardHeader>
            <CardBody>
              <Stack spacing={4}>
                <FileDropZone
                  icon={FiUploadCloud}
                  description={selectedFiles.length ? `${selectedFiles.length} file(s) selected` : 'Drop files or click to browse'}
                  helper="MP4 or MOV"
                  accept="video/mp4,video/quicktime"
                  multiple
                  onFilesSelected={handleFilesSelected}
                />
                {selectedFiles.length > 0 && (
                  <Wrap>
                    {selectedFiles.map((file) => (
                      <WrapItem key={file.name}>
                        <Tag colorScheme="purple" borderRadius="full" px={3} py={2} fontWeight="medium">
                          <Text mr={2}>{file.name}</Text>
                          <TagCloseButton onClick={() => removeFile(file.name)} />
                        </Tag>
                      </WrapItem>
                    ))}
                  </Wrap>
                )}
                {selectedFiles.length > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    leftIcon={<Icon as={FiTrash2} />}
                    onClick={() => setSelectedFiles([])}
                  >
                    Clear files
                  </Button>
                )}
              </Stack>
            </CardBody>
          </Card>

          <Card bg={cardBg} shadow="lg" borderRadius="2xl">
            <CardHeader>
              <Heading size="md">2. Choose output formats</Heading>
              <Text color="gray.500" fontSize="sm" mt={2}>
                Mix and match portrait, square, and landscape exports. Blurred variants keep full-bleed vibes.
              </Text>
            </CardHeader>
            <CardBody>
              <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                {AVAILABLE_FORMATS.map((format) => {
                  const isSelected = selectedFormats.includes(format.id);
                  return (
                    <Box
                      key={format.id}
                      borderWidth={2}
                      borderRadius="xl"
                      p={4}
                      cursor="pointer"
                      bg={isSelected ? subtleBg : cardBg}
                      borderColor={isSelected ? 'purple.400' : 'transparent'}
                      transition="all 0.2s"
                      _hover={{ borderColor: 'purple.300' }}
                      onClick={() => toggleFormat(format.id)}
                    >
                      <Heading size="sm">{format.label}</Heading>
                      <Text fontSize="sm" color="gray.500">
                        {format.subtitle}
                      </Text>
                    </Box>
                  );
                })}
              </SimpleGrid>
              <Button
                mt={4}
                variant="link"
                size="sm"
                onClick={() => setSelectedFormats(['square', 'vertical'])}
              >
                Use social preset (square + vertical)
              </Button>
            </CardBody>
          </Card>
        </SimpleGrid>

        <Card bg={cardBg} shadow="lg" borderRadius="2xl">
          <CardHeader>
            <Heading size="md">3. Render queue</Heading>
            <Text color="gray.500" fontSize="sm" mt={2}>
              Launch conversion and monitor progress. You can keep working while the backend crunches.
            </Text>
          </CardHeader>
          <CardBody>
            <Stack spacing={4}>
              <HStack spacing={3}>
                <Button
                  colorScheme="purple"
                  leftIcon={<Icon as={FiFilm} />}
                  onClick={handleStart}
                  isLoading={isSubmitting}
                  isDisabled={isProcessing}
                >
                  Convert {selectedFiles.length ? `${selectedFiles.length} video(s)` : 'videos'}
                </Button>
                {isProcessing && (
                  <Button
                    variant="outline"
                    colorScheme="red"
                    leftIcon={<Icon as={FiStopCircle} />}
                    onClick={handleCancel}
                    isLoading={isCancelling}
                  >
                    Cancel job
                  </Button>
                )}
                <Button variant="ghost" size="sm" leftIcon={<Icon as={FiTrash2} />} onClick={resetJob}>
                  Reset status
                </Button>
              </HStack>

              {status && (
                <Stack spacing={3}>
                  <Progress value={progress} size="md" colorScheme="purple" borderRadius="full" />
                  <Flex justify="space-between" align="center">
                    <Text fontSize="sm" color="gray.600">
                      Status: {status.status}
                    </Text>
                    <Text fontSize="sm" color="gray.600">
                      ETA: {formatEta(status)}
                    </Text>
                  </Flex>
                </Stack>
              )}

              {errors.length > 0 && (
                <Alert status="warning" borderRadius="md">
                  <AlertIcon />
                  <Box>
                    <AlertTitle>Some conversions failed</AlertTitle>
                    <AlertDescription>
                      <Stack spacing={1} fontSize="sm">
                        {errors.map((message, index) => (
                          <Text key={index}>{message}</Text>
                        ))}
                      </Stack>
                    </AlertDescription>
                  </Box>
                </Alert>
              )}
            </Stack>
          </CardBody>
        </Card>

        {results.length > 0 && (
          <Card bg={cardBg} shadow="lg" borderRadius="2xl">
            <CardHeader>
              <Heading size="md">Render results</Heading>
              <Text color="gray.500" fontSize="sm" mt={2}>
                Download individual formats or grab the full ZIP once you’re done reviewing.
              </Text>
            </CardHeader>
            <CardBody>
              <Stack spacing={4}>
                <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                  {results.map((result: ConversionResult) => (
                    <Card key={result.filename} borderLeftWidth={4} borderColor="purple.400">
                      <CardBody>
                        <Heading size="sm" mb={2}>
                          {result.original_name}
                        </Heading>
                        <Text fontSize="sm" color="gray.600" mb={3}>
                          {result.format_name}
                        </Text>
                        <Button
                          colorScheme="purple"
                          size="sm"
                          leftIcon={<Icon as={FiDownload} />}
                          onClick={() =>
                            window.open(
                              resolveApiUrl(`/download/${jobId}/${encodeURIComponent(result.filename)}`),
                              '_self',
                            )
                          }
                        >
                          Download
                        </Button>
                      </CardBody>
                    </Card>
                  ))}
                </SimpleGrid>
                {isCompleted && (
                  <Button
                    variant="outline"
                    colorScheme="purple"
                    leftIcon={<Icon as={FiDownload} />}
                    alignSelf="flex-start"
                    onClick={() => window.open(resolveApiUrl(`/download_zip/${jobId}`), '_self')}
                  >
                    Download all as ZIP
                  </Button>
                )}
              </Stack>
            </CardBody>
          </Card>
        )}
      </Stack>
    </Container>
  );
};

export default VideoConverterPage;
