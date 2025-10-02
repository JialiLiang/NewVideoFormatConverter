import { ChakraProvider } from '@chakra-ui/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './providers/AuthProvider';
import { AppRoutes } from './routes/AppRoutes';
import theme from './theme';

const App = () => (
  <ChakraProvider theme={theme}>
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  </ChakraProvider>
);

export default App;
