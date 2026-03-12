import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
      <p className="text-7xl font-bold text-navy">404</p>
      <h1 className="mt-4 text-2xl font-bold text-text">Page not found</h1>
      <p className="mt-2 text-sm text-text-3">
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>
      <Link
        href="/"
        className="mt-8 inline-flex items-center rounded-lg bg-navy px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-navy-dark"
      >
        &larr; Back to Home
      </Link>
    </div>
  );
}
