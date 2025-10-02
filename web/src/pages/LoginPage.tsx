import { Box, Button, Card, CardBody, Heading, Icon, Stack, Text } from '@chakra-ui/react';
import { FiArrowRight } from 'react-icons/fi';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../providers/AuthProvider';
import { ErrorState } from '../components/ErrorState';
import { LoadingState } from '../components/LoadingState';

export const LoginPage = () => {
  const { login, user, isLoading, error } = useAuth();

  if (isLoading) {
    return <LoadingState message="Checking your session..." />;
  }

  if (user) {
    return <Navigate to="/app" replace />;
  }

  return (
    <Stack minH="100vh" align="center" justify="center" px={6} py={16} spacing={10}>
      <Stack spacing={3} textAlign="center">
        <Text fontSize="sm" textTransform="uppercase" letterSpacing="widest" color="whiteAlpha.600">
          Photoroom
        </Text>
        <Heading size="xl">Creative Tools Console</Heading>
        <Text fontSize="md" color="whiteAlpha.700">
          Sign in with Google to access the React workspace and migration dashboards.
        </Text>
      </Stack>
      <Card
        maxW="lg"
        width="full"
        bg="rgba(19,18,40,0.85)"
        border="1px solid rgba(255,255,255,0.08)"
        shadow="xl"
        borderRadius="2xl"
        backdropFilter="blur(20px)"
      >
        <CardBody>
          <Stack spacing={6}>
            {error && <ErrorState description={error} />}
            <Box textAlign="center">
              <Text fontSize="sm" color="whiteAlpha.600">
                We use Google OAuth with httpOnly sessions for secure access.
              </Text>
            </Box>
            <Button size="lg" colorScheme="purple" onClick={login} rightIcon={<Icon as={FiArrowRight} />}>
              Continue with Google
            </Button>
          </Stack>
        </CardBody>
      </Card>
    </Stack>
  );
};
