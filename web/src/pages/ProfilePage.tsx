import {
  Avatar,
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
  Divider,
  FormControl,
  FormLabel,
  Heading,
  Select,
  Stack,
  Switch,
  Text,
  useColorModeValue,
} from '@chakra-ui/react';
import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../providers/AuthProvider';

type UserPreferences = {
  defaultLanding: string;
  translationMode: 'faithful' | 'creative';
  autoDownloadZip: boolean;
  themePreference: 'system' | 'light' | 'dark';
};

const PREFERENCES_STORAGE_KEY = 'creative-console:user-preferences';

const DEFAULT_PREFERENCES: UserPreferences = {
  defaultLanding: '/app',
  translationMode: 'creative',
  autoDownloadZip: false,
  themePreference: 'system',
};

export const ProfilePage = () => {
  const { user, refresh } = useAuth();
  const subtleText = useColorModeValue('gray.600', 'whiteAlpha.700');
  const helperText = useColorModeValue('gray.500', 'whiteAlpha.600');

  const [preferences, setPreferences] = useState<UserPreferences>(() => {
    try {
      const stored = localStorage.getItem(PREFERENCES_STORAGE_KEY);
      if (stored) {
        return { ...DEFAULT_PREFERENCES, ...JSON.parse(stored) };
      }
    } catch (error) {
      console.warn('Unable to load profile preferences from storage', error);
    }
    return DEFAULT_PREFERENCES;
  });

  useEffect(() => {
    try {
      localStorage.setItem(PREFERENCES_STORAGE_KEY, JSON.stringify(preferences));
    } catch (error) {
      console.warn('Unable to persist profile preferences', error);
    }
  }, [preferences]);

  const landingOptions = useMemo(
    () => [
      { value: '/app', label: 'Dashboard' },
      { value: '/app/adlocalizer', label: 'AdLocalizer' },
      { value: '/app/name-generator', label: 'Name Generator' },
      { value: '/app/video-converter', label: 'Video Converter' },
      { value: '/app/youtube-playlist', label: 'Playlist Extractor' },
    ],
    [],
  );

  if (!user) {
    return null;
  }

  return (
    <Stack spacing={6}>
      <Stack direction="row" justify="space-between" align="center">
        <Heading size="lg">Profile</Heading>
        <Button onClick={() => void refresh()} variant="outline" colorScheme="purple">
          Refresh profile
        </Button>
      </Stack>

      <Card maxW="lg">
        <CardHeader>
          <Stack direction={{ base: 'column', md: 'row' }} spacing={4} align="center">
            <Avatar size="xl" name={user.name ?? user.email} src={user.picture} />
            <Stack spacing={1} textAlign={{ base: 'center', md: 'left' }}>
              <Heading size="md">{user.name ?? 'Unnamed user'}</Heading>
              <Text color={subtleText}>{user.email}</Text>
              {user.locale && (
                <Badge colorScheme="purple" width="fit-content">
                  locale: {user.locale}
                </Badge>
              )}
            </Stack>
          </Stack>
        </CardHeader>
        <CardBody>
          <Stack spacing={2}>
            <Text fontSize="sm" color={subtleText}>
              Google authentication provides basic profile attributes. Extend this card when additional account metadata becomes available.
            </Text>
            {user.id && (
              <Text fontSize="xs" color={helperText}>
                Internal id: {user.id}
              </Text>
            )}
          </Stack>
        </CardBody>
      </Card>

      <Card maxW="3xl">
        <CardHeader>
          <Heading size="md">Preferences</Heading>
        </CardHeader>
        <CardBody>
          <Stack spacing={6}>
            <FormControl>
              <FormLabel>Default landing page</FormLabel>
              <Select
                value={preferences.defaultLanding}
                onChange={(event) =>
                  setPreferences((prev) => ({ ...prev, defaultLanding: event.target.value }))
                }
              >
                {landingOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
              <Text fontSize="sm" color={helperText} mt={2}>
                Choose where the React shell should route after you sign in.
              </Text>
            </FormControl>

            <Divider />

            <FormControl>
              <FormLabel>Preferred translation mode</FormLabel>
              <Select
                value={preferences.translationMode}
                onChange={(event) =>
                  setPreferences((prev) => ({
                    ...prev,
                    translationMode: event.target.value as UserPreferences['translationMode'],
                  }))
                }
              >
                <option value="faithful">Faithful — close to source copy</option>
                <option value="creative">Creative — localized tone</option>
              </Select>
              <Text fontSize="sm" color={helperText} mt={2}>
                This preset seeds the AdLocalizer translation widget; you can still override per session.
              </Text>
            </FormControl>

            <Divider />

            <FormControl display="flex" alignItems="center" justifyContent="space-between">
              <Box>
                <FormLabel mb={0}>Auto-download ZIP after render</FormLabel>
                <Text fontSize="sm" color={helperText}>
                  When enabled, the video converter grabs the complete ZIP as soon as a job finishes.
                </Text>
              </Box>
              <Switch
                isChecked={preferences.autoDownloadZip}
                colorScheme="purple"
                onChange={(event) =>
                  setPreferences((prev) => ({ ...prev, autoDownloadZip: event.target.checked }))
                }
              />
            </FormControl>

            <Divider />

            <FormControl>
              <FormLabel>Theme preference</FormLabel>
              <Select
                value={preferences.themePreference}
                onChange={(event) =>
                  setPreferences((prev) => ({
                    ...prev,
                    themePreference: event.target.value as UserPreferences['themePreference'],
                  }))
                }
              >
                <option value="system">Match system</option>
                <option value="light">Light</option>
                <option value="dark">Dark</option>
              </Select>
              <Text fontSize="sm" color={helperText} mt={2}>
                Applied on next reload. A future update will wire this into a live color-mode switch.
              </Text>
            </FormControl>

            <Button
              variant="outline"
              colorScheme="purple"
              alignSelf="flex-start"
              onClick={() => setPreferences(DEFAULT_PREFERENCES)}
            >
              Restore defaults
            </Button>
          </Stack>
        </CardBody>
      </Card>
    </Stack>
  );
};
