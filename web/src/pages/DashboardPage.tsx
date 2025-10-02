import {
  Box,
  Button,
  Card,
  CardBody,
  Heading,
  Icon,
  SimpleGrid,
  Stack,
  Text,
} from '@chakra-ui/react';
import { FiArrowUpRight, FiExternalLink } from 'react-icons/fi';
import { Link as RouterLink } from 'react-router-dom';

const reactLinks = [
  {
    label: 'AdLocalizer (React)',
    description: 'Translate, generate voiceovers, and mix localized videos in the new UI.',
    to: '/app/adlocalizer',
  },
  {
    label: 'Name Generator (React)',
    description: 'Live preview, validator, and AI corrections for AdManage naming.',
    to: '/app/name-generator',
  },
  {
    label: 'Video Converter (React)',
    description: 'Convert batches into portrait, square, and landscape with blurred fills.',
    to: '/app/video-converter',
  },
  {
    label: 'Playlist Extractor (React)',
    description: 'Parse YouTube playlist IDs and metadata for downstream automation.',
    to: '/app/youtube-playlist',
  },
];

const legacyLinks = [{ label: 'Video Converter', href: '/video-converter' }];

const heroStats = [
  { label: 'React modules', value: '3 live' },
  { label: 'Legacy tools', value: '4 migrating' },
  { label: 'Auth status', value: 'Google OAuth' },
];

export const DashboardPage = () => (
  <Stack spacing={12}>
    <Box
      bgGradient="linear(to-br, rgba(112,76,255,0.35), rgba(244,114,182,0.2))"
      borderRadius="3xl"
      px={{ base: 6, md: 12 }}
      py={{ base: 10, md: 14 }}
      boxShadow="0 30px 70px -20px rgba(112, 76, 255, 0.45)"
      border="1px solid rgba(255,255,255,0.1)"
    >
      <Stack spacing={6} maxW="3xl">
        <Stack spacing={2}>
          <Text fontSize="sm" textTransform="uppercase" letterSpacing="widest" color="whiteAlpha.700">
            Welcome back
          </Text>
          <Heading size="lg" lineHeight="1.2">
            Ship creative workflows faster with the new React + Chakra shell.
          </Heading>
          <Text fontSize="md" color="whiteAlpha.700">
            Monitor migration progress, jump into localized voiceovers, and keep the legacy toolkit one click away while we
            complete the rollout.
          </Text>
        </Stack>
        <SimpleGrid columns={{ base: 1, sm: 3 }} spacing={6}>
          {heroStats.map((stat) => (
            <Box
              key={stat.label}
              bg="rgba(10,9,24,0.55)"
              borderRadius="2xl"
              px={5}
              py={4}
              border="1px solid rgba(255,255,255,0.08)"
            >
              <Text fontSize="xs" textTransform="uppercase" letterSpacing="widest" color="whiteAlpha.600" mb={2}>
                {stat.label}
              </Text>
              <Text fontSize="xl" fontWeight="semibold">
                {stat.value}
              </Text>
            </Box>
          ))}
        </SimpleGrid>
      </Stack>
    </Box>

    <Stack spacing={6}>
      <Heading size="md">React workspace</Heading>
      <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
        {reactLinks.map((link) => (
          <Card
            key={link.to}
            bg="rgba(19,18,40,0.85)"
            border="1px solid rgba(255,255,255,0.04)"
            transition="all 0.2s"
            _hover={{ borderColor: 'rgba(255,255,255,0.18)', transform: 'translateY(-4px)' }}
          >
            <CardBody>
              <Stack spacing={4}>
                <Stack spacing={1}>
                  <Text fontSize="sm" color="whiteAlpha.600">
                    React module
                  </Text>
                  <Heading size="md">{link.label}</Heading>
                </Stack>
                <Text fontSize="sm" color="whiteAlpha.700">
                  {link.description}
                </Text>
                <Button
                  as={RouterLink}
                  to={link.to}
                  rightIcon={<Icon as={FiArrowUpRight} />}
                  colorScheme="purple"
                  alignSelf="flex-start"
                >
                  Open workspace
                </Button>
              </Stack>
            </CardBody>
          </Card>
        ))}
      </SimpleGrid>
    </Stack>

    <Stack spacing={6}>
      <Heading size="md">Legacy fallback</Heading>
      <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6}>
        {legacyLinks.map((link) => (
          <Card
            key={link.href}
            bg="rgba(19,18,40,0.7)"
            border="1px solid rgba(255,255,255,0.05)"
          >
            <CardBody>
              <Stack spacing={4}>
                <Stack spacing={1}>
                  <Text fontSize="sm" color="whiteAlpha.600">
                    Flask template
                  </Text>
                  <Heading size="md">{link.label}</Heading>
                </Stack>
                <Text fontSize="sm" color="whiteAlpha.700">
                  Opens the legacy Flask-rendered experience. Use until the React port lands.
                </Text>
                <Button
                  as="a"
                  href={link.href}
                  variant="outline"
                  rightIcon={<Icon as={FiExternalLink} />}
                  colorScheme="purple"
                  alignSelf="flex-start"
                >
                  Launch legacy
                </Button>
              </Stack>
            </CardBody>
          </Card>
        ))}
      </SimpleGrid>
    </Stack>
  </Stack>
);
