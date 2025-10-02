export interface UserProfile {
  id: string;
  email: string;
  name?: string;
  given_name?: string;
  family_name?: string;
  picture?: string;
  locale?: string;
}
