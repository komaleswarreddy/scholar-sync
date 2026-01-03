import { redirect } from 'next/navigation';

export default async function HomePage() {
  // Temporarily allow access without Clerk for development
  // TODO: Re-enable authentication once Clerk keys are configured
  // const clerkKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  
  // if (clerkKey && !clerkKey.includes('...')) {
  //   // Clerk is configured, check authentication
  //   // const user = await currentUser();
  //   // if (!user) {
  //   //   redirect('/sign-in');
  //   // }
  // }
  
  // Extract subdomain from host
  // In production, this would be handled by middleware
  redirect('/dashboard');
}

