import { Navigate, useRoutes } from 'react-router-dom';
import { LoginPage } from '../pages/LoginPage';
import { DashboardPage } from '../pages/DashboardPage';
import { ProfilePage } from '../pages/ProfilePage';
import { NameGeneratorPage } from '../pages/NameGeneratorPage';
import { AdLocalizerPage } from '../pages/AdLocalizerPage';
import { VideoConverterPage } from '../pages/VideoConverterPage';
import { YoutubePlaylistPage } from '../pages/YoutubePlaylistPage';
import { AppLayout } from '../layouts/AppLayout';
import { ProtectedRoute } from './ProtectedRoute';

export const AppRoutes = () =>
  useRoutes([
    { path: '/', element: <Navigate to="/app" replace /> },
    { path: '/login', element: <LoginPage /> },
    {
      element: <ProtectedRoute />,
      children: [
        {
          path: '/app',
          element: <AppLayout />,
          children: [
            { index: true, element: <DashboardPage /> },
            { path: 'profile', element: <ProfilePage /> },
            { path: 'name-generator', element: <NameGeneratorPage /> },
            { path: 'adlocalizer', element: <AdLocalizerPage /> },
            { path: 'video-converter', element: <VideoConverterPage /> },
            { path: 'youtube-playlist', element: <YoutubePlaylistPage /> },
          ],
        },
      ],
    },
    { path: '*', element: <Navigate to="/app" replace /> },
  ]);
