import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="flex flex-col items-center justify-center flex-1 text-center px-4">
      <h1 className="text-4xl font-bold mb-4">Margrete RPC</h1>
      <p className="text-fd-muted-foreground text-lg max-w-xl mb-8">
        Script UMIGURI/Margrete charts with Python.
      </p>
      <div className="flex gap-4 flex-wrap justify-center">
        <Link
          href="/docs"
          className="bg-fd-primary text-fd-primary-foreground px-6 py-2 rounded-md font-medium hover:opacity-90 transition-opacity"
        >
          Get Started
        </Link>
        <a
          href="https://github.com/Foahh/margrete-rpc"
          className="border border-fd-border px-6 py-2 rounded-md font-medium hover:bg-fd-muted transition-colors"
        >
          GitHub
        </a>
      </div>
    </main>
  );
}
