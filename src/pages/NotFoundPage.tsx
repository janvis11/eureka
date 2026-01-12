import { Link } from 'react-router-dom';

const NotFoundPage = () => (
  <section className="min-h-screen bg-black text-white flex items-center justify-center px-6 text-center">
    <div className="space-y-6">
      <p className="text-xs uppercase tracking-[0.4em] text-white/50">404</p>
      <h1 className="text-5xl font-bold">Signal Lost</h1>
      <p className="text-white/60 max-w-md">
        The research artifact you&apos;re looking for doesn&apos;t exist. Return to base camp and try again.
      </p>
      <Link to="/" className="inline-flex px-8 py-3 bg-white text-black font-semibold rounded-full">
        Back to Home
      </Link>
    </div>
  </section>
);

export default NotFoundPage;

