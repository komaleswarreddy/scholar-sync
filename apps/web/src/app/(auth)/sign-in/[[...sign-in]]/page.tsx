import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <SignIn 
        // This component automatically reads the "redirect_url" 
        // provided by the middleware to handle deep links.
        // Default redirect for non-deep-link sign-ins
        redirectUrl="/home"
        appearance={{
          elements: {
            formButtonPrimary: "bg-blue-600 hover:bg-blue-700",
          }
        }}
      />
    </div>
  );
}
