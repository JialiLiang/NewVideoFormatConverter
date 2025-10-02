import {
  Avatar,
  Box,
  Button,
  Flex,
  HStack,
  Icon,
  IconButton,
  Stack,
  Text,
} from '@chakra-ui/react';
import { FiCompass, FiFilm, FiHeadphones, FiList, FiLogOut, FiType, FiUser } from 'react-icons/fi';
import { Outlet, Link as RouterLink, useLocation } from 'react-router-dom';
import { useAuth } from '../providers/AuthProvider';

const NAV_ITEMS = [
  { label: 'Overview', to: '/app', icon: FiCompass },
  { label: 'AdLocalizer', to: '/app/adlocalizer', icon: FiHeadphones },
  { label: 'Name Generator', to: '/app/name-generator', icon: FiType },
  { label: 'Video Converter', to: '/app/video-converter', icon: FiFilm },
  { label: 'Playlist Extractor', to: '/app/youtube-playlist', icon: FiList },
  { label: 'Profile', to: '/app/profile', icon: FiUser },
];

const isActivePath = (currentPath: string, target: string) =>
  currentPath === target || (target !== '/app' && currentPath.startsWith(`${target}/`));

export const AppLayout = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  return (
    <Flex
      minH="100vh"
      bgGradient="radial(120% 120% at 50% 0%, rgba(112,76,255,0.35), rgba(8,7,22,1))"
      color="whiteAlpha.900"
    >
      <Flex
        as="aside"
        direction="column"
        w="72"
        px={8}
        py={10}
        gap={8}
        display={{ base: 'none', lg: 'flex' }}
        borderRight="1px solid rgba(255,255,255,0.06)"
        bg="linear-gradient(180deg, rgba(25,17,48,0.65) 0%, rgba(12,10,26,0.65) 100%)"
        backdropFilter="blur(22px)"
      >
        <Stack spacing={1}>
          <Text fontSize="sm" letterSpacing="widest" textTransform="uppercase" color="whiteAlpha.600">
            Photoroom
          </Text>
          <Text fontSize="xl" fontWeight="semibold">
            Creative Console
          </Text>
        </Stack>

        <Stack spacing={2}>
          {NAV_ITEMS.map((item) => {
            const active = isActivePath(location.pathname, item.to);
            return (
              <Button
                key={item.to}
                as={RouterLink}
                to={item.to}
                justifyContent="flex-start"
                leftIcon={<Icon as={item.icon} boxSize={5} />}
                variant={active ? 'solid' : 'ghost'}
                colorScheme="purple"
                bg={active ? 'rgba(112,76,255,0.25)' : 'transparent'}
                _hover={{ bg: 'rgba(112,76,255,0.2)' }}
              >
                {item.label}
              </Button>
            );
          })}
        </Stack>

        <Stack spacing={3} mt="auto">
          {user && (
            <HStack spacing={3} align="center">
              <Avatar size="sm" name={user.name ?? user.email} src={user.picture} />
              <Box>
                <Text fontWeight="medium">{user.name ?? 'Signed in'}</Text>
                <Text fontSize="sm" color="whiteAlpha.600">
                  {user.email}
                </Text>
              </Box>
            </HStack>
          )}
          <Button variant="outline" onClick={() => void logout()}>
            Log out
          </Button>
        </Stack>
      </Flex>

      <Flex flex="1" direction="column">
        <Box
          as="header"
          px={{ base: 4, md: 8 }}
          py={4}
          borderBottom="1px solid rgba(255,255,255,0.08)"
          bg="rgba(10,9,24,0.65)"
          backdropFilter="blur(18px)"
        >
          <Flex align="center" justify="space-between">
            <Stack spacing={1} display={{ base: 'flex', lg: 'none' }}>
              <Text fontSize="sm" letterSpacing="widest" textTransform="uppercase" color="whiteAlpha.600">
                Photoroom
              </Text>
              <Text fontSize="lg" fontWeight="semibold">
                Creative Console
              </Text>
            </Stack>
            <HStack spacing={2} display={{ base: 'flex', lg: 'none' }}>
              {NAV_ITEMS.map((item) => {
                const active = isActivePath(location.pathname, item.to);
                return (
                  <IconButton
                    key={item.to}
                    as={RouterLink}
                    to={item.to}
                    aria-label={item.label}
                    icon={<Icon as={item.icon} />}
                    variant={active ? 'solid' : 'ghost'}
                    colorScheme="purple"
                  />
                );
              })}
              <IconButton
                aria-label="Log out"
                icon={<Icon as={FiLogOut} />}
                variant="ghost"
                colorScheme="purple"
                onClick={() => void logout()}
                display={{ base: 'inline-flex', md: 'none' }}
              />
            </HStack>
            {user && (
              <HStack spacing={3} display={{ base: 'none', md: 'flex' }}>
                <Avatar size="sm" name={user.name ?? user.email} src={user.picture} />
                <Box textAlign="right">
                  <Text fontSize="sm" fontWeight="medium">
                    {user.name ?? user.email}
                  </Text>
                  <Text fontSize="xs" color="whiteAlpha.600">
                    {user.email}
                  </Text>
                </Box>
              </HStack>
            )}
            <Button size="sm" variant="outline" onClick={() => void logout()} display={{ base: 'none', md: 'inline-flex' }}>
              Log out
            </Button>
          </Flex>
        </Box>

        <Box as="main" flex="1" px={{ base: 4, md: 8 }} py={{ base: 6, md: 10 }}>
          <Box maxW="7xl" mx="auto">
            <Outlet />
          </Box>
        </Box>
      </Flex>
    </Flex>
  );
};
