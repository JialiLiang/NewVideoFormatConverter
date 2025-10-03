import {
  Alert,
  AlertDescription,
  AlertIcon,
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
  Heading,
  HStack,
  Icon,
  Input,
  InputGroup,
  InputRightElement,
  SimpleGrid,
  Spinner,
  Stack,
  Stat,
  StatLabel,
  StatNumber,
  Table,
  Tbody,
  Td,
  Text,
  Textarea,
  Tr,
  useColorModeValue,
  useToast,
} from '@chakra-ui/react';
import { FiExternalLink, FiLink, FiList, FiPlay, FiRefreshCcw } from 'react-icons/fi';
import { FaYoutube } from 'react-icons/fa';
import { isAxiosError } from 'axios';
import { useMemo, useState } from 'react';
import { extractPlaylist, type ExtractPlaylistResponse } from '../api/youtube';

const formatDuration = (seconds?: number) => {
  if (!seconds || Number.isNaN(seconds)) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const parts = [m.toString().padStart(2, '0'), s.toString().padStart(2, '0')];
  return h > 0 ? `${h}:${parts.join(':')}` : `${m}:${s.toString().padStart(2, '0')}`;
};

const formatViews = (views?: number) => {
  if (!views) return '—';
  if (views < 1_000) return views.toString();
  if (views < 1_000_000) return `${(views / 1_000).toFixed(1)}K`;
  if (views < 1_000_000_000) return `${(views / 1_000_000).toFixed(1)}M`;
  return `${(views / 1_000_000_000).toFixed(1)}B`;
};

export const YoutubePlaylistPage = () => {
  const toast = useToast();
  const cardBg = useColorModeValue('white', 'rgba(19,18,40,0.85)');
  const heroGradient = useColorModeValue(
    'linear(to-r, purple.500, pink.500)',
    'linear(to-r, rgba(112,76,255,0.7), rgba(236,72,153,0.5))',
  );
  const bodyTextColor = useColorModeValue('gray.600', 'whiteAlpha.700');

  const [playlistUrl, setPlaylistUrl] = useState('');
  const [result, setResult] = useState<ExtractPlaylistResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const hasResults = result?.success && !!result.video_ids?.length;

  const totalVideos = result?.total_videos ?? result?.video_ids?.length ?? 0;

  const handleExtract = async () => {
    const url = playlistUrl.trim();
    if (!url) {
      toast({ status: 'warning', title: 'Enter a playlist URL first' });
      return;
    }
    setIsLoading(true);
    setResult(null);
    try {
      const response = await extractPlaylist(url);
      setResult(response);
      toast({
        status: 'success',
        title: 'Playlist processed',
        description: response.playlist_title ? `Found ${response.total_videos ?? 0} videos` : undefined,
      });
    } catch (error) {
      if (isAxiosError(error)) {
        const data = error.response?.data as ExtractPlaylistResponse | undefined;
        setResult(data ?? null);
        const message = data?.error ?? 'Unable to process playlist';
        toast({ status: 'error', title: 'Playlist extraction failed', description: message });
      } else {
        toast({ status: 'error', title: 'Playlist extraction failed', description: (error as Error).message });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopyIds = async () => {
    if (!result?.video_ids_text) return;
    try {
      await navigator.clipboard.writeText(result.video_ids_text);
      toast({ status: 'success', title: 'Video IDs copied to clipboard' });
    } catch (error) {
      toast({ status: 'error', title: 'Unable to copy', description: (error as Error).message });
    }
  };

  const heroStats = useMemo(
    () => [
      { label: 'Playlist videos', value: totalVideos ? totalVideos.toString() : '—' },
      { label: 'Latest run', value: hasResults ? 'Success' : '—' },
      { label: 'Extraction mode', value: 'yt-dlp (flat JSON)' },
    ],
    [hasResults, totalVideos],
  );

  return (
    <Container maxW="7xl" py={10} px={{ base: 4, md: 6 }}>
      <Stack spacing={12}>
        <Box bgGradient={heroGradient} borderRadius="2xl" color="white" p={{ base: 6, md: 10 }} shadow="xl">
          <Stack spacing={6} maxW="3xl">
            <HStack spacing={3} align="center">
              <Box
                bg="rgba(255,0,0,0.2)"
                borderRadius="full"
                p={3}
                display="flex"
                alignItems="center"
                justifyContent="center"
              >
                <Icon as={FaYoutube} boxSize={7} color="white" />
              </Box>
              <Heading size="lg">YouTube Playlist Extractor</Heading>
            </HStack>
            <Text fontSize={{ base: 'md', md: 'lg' }} color="whiteAlpha.900">
              Grab clean video IDs, titles, and metadata for Rapid ingestion workflows. Designed for long playlists and
              private links (with credentials configured in backend).
            </Text>
            <Divider borderColor="whiteAlpha.400" />
            <SimpleGrid columns={{ base: 1, sm: 3 }} spacing={4}>
              {heroStats.map((stat) => (
                <Box
                  key={stat.label}
                  bg="whiteAlpha.200"
                  borderRadius="lg"
                  px={4}
                  py={3}
                  borderWidth="1px"
                  borderColor="whiteAlpha.300"
                >
                  <Stat>
                    <StatLabel color="whiteAlpha.700">{stat.label}</StatLabel>
                    <StatNumber fontSize="lg">{stat.value}</StatNumber>
                  </Stat>
                </Box>
              ))}
            </SimpleGrid>
          </Stack>
        </Box>

        <Card bg={cardBg} shadow="lg" borderRadius="2xl">
          <CardHeader>
            <Heading size="md">1. Paste playlist URL</Heading>
            <Text color={bodyTextColor} fontSize="sm" mt={2}>
              Works with public, unlisted, or private playlists (requires configured cookies on the backend for restricted
              content).
            </Text>
          </CardHeader>
          <CardBody>
            <Stack spacing={4}>
              <FormControl>
                <FormLabel>YouTube playlist link</FormLabel>
                <InputGroup size="lg">
                  <Input
                    value={playlistUrl}
                    onChange={(event) => setPlaylistUrl(event.target.value)}
                    placeholder="https://www.youtube.com/playlist?list=..."
                    pr="5rem"
                  />
                  <InputRightElement width="4.5rem">
                    <Icon as={FiLink} color="purple.300" />
                  </InputRightElement>
                </InputGroup>
              </FormControl>
              <HStack spacing={3}>
                <Button
                  colorScheme="purple"
                  leftIcon={isLoading ? <Spinner size="sm" /> : <Icon as={FiRefreshCcw} />}
                  onClick={handleExtract}
                  isDisabled={isLoading}
                >
                  {isLoading ? 'Extracting…' : 'Extract playlist'}
                </Button>
                <Button variant="ghost" onClick={() => setPlaylistUrl('')} isDisabled={isLoading}>
                  Clear
                </Button>
              </HStack>
              {result && !result.success && result.error && (
                <Alert status="error" borderRadius="md">
                  <AlertIcon />
                  <AlertDescription>{result.error}</AlertDescription>
                </Alert>
              )}
            </Stack>
          </CardBody>
        </Card>

        {hasResults && result && (
          <Stack spacing={10}>
            <Card bg={cardBg} shadow="lg" borderRadius="2xl">
              <CardHeader>
                <Heading size="md">2. Review & export IDs</Heading>
                <Text color={bodyTextColor} fontSize="sm" mt={2}>
                  Copy the cleaned list or inspect metadata before sending downstream.
                </Text>
              </CardHeader>
              <CardBody>
                <Stack spacing={6}>
                  <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
                    <Box>
                      <Text fontSize="sm" color={bodyTextColor}>
                        Playlist
                      </Text>
                      <Text fontWeight="semibold">{result.playlist_title ?? 'Untitled playlist'}</Text>
                      <Text fontSize="sm" color={bodyTextColor}>
                        {result.playlist_url}
                      </Text>
                    </Box>
                    <Box>
                      <Text fontSize="sm" color={bodyTextColor}>
                        Total videos
                      </Text>
                      <Heading size="md">{totalVideos}</Heading>
                    </Box>
                    <Box>
                      <Text fontSize="sm" color={bodyTextColor}>
                        Export actions
                      </Text>
                      <HStack spacing={2} mt={2}>
                        <Button size="sm" variant="outline" onClick={handleCopyIds} leftIcon={<Icon as={FiList} />}>
                          Copy IDs
                        </Button>
                        <Button
                          as="a"
                          size="sm"
                          variant="ghost"
                          href={result.playlist_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          leftIcon={<Icon as={FiExternalLink} />}
                        >
                          Open playlist
                        </Button>
                      </HStack>
                    </Box>
                  </SimpleGrid>
                  <Box>
                    <Text fontSize="sm" color={bodyTextColor} mb={2}>
                      Video IDs (one per line)
                    </Text>
                    <Textarea value={result.video_ids_text ?? ''} minH="200px" readOnly />
                  </Box>
                </Stack>
              </CardBody>
            </Card>

            <Card bg={cardBg} shadow="lg" borderRadius="2xl">
          <CardHeader>
            <Heading size="md">3. Playlist summary</Heading>
            <Text color={bodyTextColor} fontSize="sm" mt={2}>
              Quick glance at each item before you bulk import.
            </Text>
              </CardHeader>
              <CardBody>
                <Table variant="simple" size="md">
                  <Tbody>
                    {result.videos?.map((video, index) => (
                      <Tr key={video.video_id} _hover={{ bg: 'rgba(112,76,255,0.06)' }}>
                        <Td width="40px">
                          <Badge colorScheme="purple" variant="subtle">
                            {index + 1}
                          </Badge>
                        </Td>
                        <Td>
                          <Stack spacing={1}>
                            <HStack spacing={2}>
                              <Icon as={FiPlay} />
                              <Text fontWeight="medium">{video.title}</Text>
                            </HStack>
                            <Text fontSize="sm" color={bodyTextColor}>
                              {video.url}
                            </Text>
                          </Stack>
                        </Td>
                        <Td width="120px">{formatDuration(video.duration)}</Td>
                        <Td width="120px">{formatViews(video.views)}</Td>
                        <Td width="180px">{video.author ?? 'Unknown'}</Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </CardBody>
            </Card>
          </Stack>
        )}
      </Stack>
    </Container>
  );
};

export default YoutubePlaylistPage;
