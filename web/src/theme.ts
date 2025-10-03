import { extendTheme, type ThemeConfig, type StyleFunctionProps } from '@chakra-ui/react';
import { mode } from '@chakra-ui/theme-tools';

const config: ThemeConfig = {
  initialColorMode: 'dark',
  useSystemColorMode: false,
};

const theme = extendTheme({
  config,
  fonts: {
    heading:
      "'Space Grotesk', 'Inter', 'Noto Sans', 'Noto Sans SC', 'Noto Sans JP', 'Noto Sans KR', 'Noto Sans Thai', 'Noto Sans Arabic', 'Noto Sans Devanagari', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    body:
      "'Inter', 'Noto Sans', 'Noto Sans SC', 'Noto Sans JP', 'Noto Sans KR', 'Noto Sans Thai', 'Noto Sans Arabic', 'Noto Sans Devanagari', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  },
  colors: {
    brand: {
      50: '#f3f0ff',
      100: '#dcd2ff',
      200: '#c2b3ff',
      300: '#a694ff',
      400: '#8a75ff',
      500: '#704cff',
      600: '#5938db',
      700: '#4328b7',
      800: '#2d1c93',
      900: '#1c116f',
    },
  },
  styles: {
    global: {
      body: {
        bg: '#08071a',
        color: 'whiteAlpha.900',
        backgroundImage:
          'radial-gradient(120% 120% at 50% 0%, rgba(112,76,255,0.35), rgba(8,7,22,1))',
      },
    },
  },
  components: {
    Button: {
      baseStyle: {
        borderRadius: 'xl',
        fontWeight: '600',
        transition: 'all 0.15s ease-out',
      },
      variants: {
        solid: {
          bgGradient: 'linear(to-r, brand.500, pink.400)',
          _hover: { bgGradient: 'linear(to-r, brand.400, pink.300)', transform: 'translateY(-1px)' },
          _active: { transform: 'translateY(0)' },
        },
        outline: (props: StyleFunctionProps) => ({
          borderWidth: '1.5px',
          borderColor: mode('brand.500', 'rgba(255,255,255,0.6)')(props),
          color: mode('brand.600', 'whiteAlpha.900')(props),
          _hover: {
            bg: mode('brand.50', 'rgba(255,255,255,0.12)')(props),
          },
        }),
        ghost: (props: StyleFunctionProps) => ({
          color: mode('brand.600', 'whiteAlpha.900')(props),
          _hover: {
            bg: mode('brand.50', 'rgba(255,255,255,0.12)')(props),
          },
        }),
      },
    },
    Card: {
      baseStyle: {
        borderRadius: '2xl',
        border: '1px solid rgba(255,255,255,0.06)',
        bg: 'rgba(16,14,32,0.9)',
        backdropFilter: 'blur(18px)',
        boxShadow: '0 20px 55px -25px rgba(112,76,255,0.6)',
      },
    },
  },
});

export default theme;
