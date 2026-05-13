import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import clsx from 'clsx';

type NavItem = {
  name: string;
  path: string;
};

const navItems: NavItem[] = [
  { name: 'HOME', path: '/' },
  { name: 'WORKSPACE', path: '/workspace' },
  { name: 'CHAT', path: '/chat' },
  { name: 'GRAPH', path: '/knowledge-graph' },
  { name: 'DISCOVER', path: '/discovery' },
  { name: 'HYPOTHESIS', path: '/hypothesis' }
];

const Navbar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [isScrolled, setIsScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const isDarkRoute = useMemo(
    () => ['/', '/workspace', '/chat', '/knowledge-graph', '/discovery', '/hypothesis'].includes(location.pathname),
    [location.pathname]
  );

  return (
    <nav
      className={clsx(
        'fixed top-0 left-0 right-0 z-50 transition-all duration-300',
        isScrolled
          ? isDarkRoute
            ? 'bg-black/90 backdrop-blur-xl border-b border-white/10'
            : 'bg-white/90 backdrop-blur-xl border-b border-black/10'
          : 'bg-transparent'
      )}
    >
      <div className="max-w-7xl mx-auto px-6 md:px-12">
        <div className="flex items-center justify-between h-20">
          <Link to="/" className="flex items-center space-x-3 group">
            <img
              src="/eureka_logo.png"
              alt="Eureka"
              className={clsx(
                'w-10 h-10 object-cover border transition-all duration-300',
                isDarkRoute ? 'border-white/30' : 'border-black/20'
              )}
            />
            <span
              className={clsx('text-xl font-bold tracking-tighter', isDarkRoute ? 'text-white' : 'text-black')}
            >
              EUREKA
            </span>
          </Link>

          <div className="hidden md:flex items-center space-x-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={clsx(
                    'relative px-4 py-2 text-xs font-bold tracking-wider transition-all duration-300',
                    {
                      'text-black bg-white': isActive && isDarkRoute,
                      'text-white bg-black': isActive && !isDarkRoute,
                      'text-white hover:text-black hover:bg-white': !isActive && isDarkRoute,
                      'text-black hover:text-white hover:bg-black': !isActive && !isDarkRoute
                    }
                  )}
                >
                  {item.name}
                </Link>
              );
            })}
          </div>

          <button
            onClick={() => navigate('/workspace')}
            aria-label="Open research workspace"
            className={clsx(
              'px-6 py-2.5 text-xs font-bold tracking-wider transition-all duration-300',
              isDarkRoute ? 'bg-white text-black hover:bg-gray-200' : 'bg-black text-white hover:bg-gray-800'
            )}
          >
            UPLOAD
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
