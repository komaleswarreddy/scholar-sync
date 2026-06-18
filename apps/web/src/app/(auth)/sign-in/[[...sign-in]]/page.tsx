import Link from 'next/link';
import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 px-4">
      <SignIn 
        redirectUrl="/home"
        appearance={{
          elements: {
            formButtonPrimary: "bg-blue-600 hover:bg-blue-700",
          }
        }}
      />
      <div className="flex flex-wrap items-center justify-center gap-3">
        <Link
          href="/admin/login"
          className="rounded-lg border border-border-default bg-white px-5 py-2.5 text-sm font-medium text-text-primary shadow-sm hover:bg-surface-hover"
        >
          Admin
        </Link>
        <Link
          href="/teacher/login"
          className="rounded-lg border border-border-default bg-white px-5 py-2.5 text-sm font-medium text-text-primary shadow-sm hover:bg-surface-hover"
        >
          Teacher
        </Link>
      </div>
    </div>
  );
}
