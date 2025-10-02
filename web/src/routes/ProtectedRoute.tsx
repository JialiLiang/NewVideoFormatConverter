import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../providers/AuthProvider';
import { LoadingState } from '../components/LoadingState';

export const ProtectedRoute = () => {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <LoadingState />;
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
};
