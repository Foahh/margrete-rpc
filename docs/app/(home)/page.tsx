import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center px-4 text-center">
      <h1 className="mb-4 text-4xl font-bold">Margrete RPC</h1>
      <p className="text-fd-muted-foreground mb-8 max-w-xl text-lg">
        Script UMIGURI/Margrete charts with Python.
      </p>
      <div className="flex flex-wrap justify-center gap-4">
        <Link
          href="/docs"
          className="bg-fd-primary text-fd-primary-foreground rounded-md px-6 py-2 font-medium transition-opacity hover:opacity-90"
        >
          Get Started
        </Link>
      </div>
    </main>
  );
}
