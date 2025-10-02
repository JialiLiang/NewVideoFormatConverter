import { Alert, AlertDescription, AlertIcon, AlertTitle } from '@chakra-ui/react';

export const ErrorState = ({ title, description }: { title?: string; description: string }) => (
  <Alert status="error" borderRadius="md">
    <AlertIcon />
    <AlertTitle mr={2}>{title ?? 'Something went wrong'}</AlertTitle>
    <AlertDescription>{description}</AlertDescription>
  </Alert>
);
