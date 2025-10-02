import { Center, Spinner, Text, VStack } from '@chakra-ui/react';

export const LoadingState = ({ message = 'Loading...' }: { message?: string }) => (
  <Center minH="60vh">
    <VStack spacing={4} align="center">
      <Spinner size="lg" thickness="4px" speed="0.65s" />
      <Text fontSize="sm" color="whiteAlpha.700">
        {message}
      </Text>
    </VStack>
  </Center>
);
