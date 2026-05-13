import { Link } from 'react-router-dom';

const Footer = () => {
  const currentYear = 2025;
  
  const navLinks = [
    { name: 'Chat', path: '/chat' },
    { name: 'Graph', path: '/knowledge-graph' },
    { name: 'Discovery', path: '/discovery' },
    { name: 'Hypotheses', path: '/hypothesis' }
  ];

  return (
    <footer className="bg-black text-white border-t border-white/20 py-16 px-6 md:px-12">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-12">
          <div className="md:col-span-2">
            <h3 className="text-3xl font-bold mb-4">EUREKA</h3>
            <p className="text-gray-400 text-sm max-w-md leading-relaxed">
              AI-powered scientific discovery platform. Deconstructing literature, reconstructing knowledge.
            </p>
          </div>

          <div>
            <h4 className="font-bold mb-4 text-sm uppercase tracking-wider">Navigation</h4>
            <ul className="space-y-2 text-sm text-gray-400">
              {navLinks.map((link) => (
                <li key={link.path}>
                  <Link to={link.path} className="hover:text-white transition-colors">
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="font-bold mb-4 text-sm uppercase tracking-wider">Resources</h4>
            <ul className="space-y-2 text-sm text-gray-400">
              <li>
                <a 
                  href="https://github.com" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="hover:text-white transition-colors"
                >
                  GitHub
                </a>
              </li>
              <li>
                <a 
                  href="https://docs.eureka.ai" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="hover:text-white transition-colors"
                >
                  Documentation
                </a>
              </li>
              <li>
                <a 
                  href="mailto:contact@eureka.ai" 
                  className="hover:text-white transition-colors"
                >
                  Contact
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="pt-8 border-t border-white/20 flex flex-col md:flex-row justify-between items-center text-xs text-gray-500">
          <span>© {currentYear} EUREKA. ALL RIGHTS RESERVED.</span>
          <div className="flex space-x-6 mt-4 md:mt-0">
            <span className="hover:text-white transition-colors cursor-pointer">PRIVACY</span>
            <span className="hover:text-white transition-colors cursor-pointer">TERMS</span>
            <span className="hover:text-white transition-colors cursor-pointer">SECURITY</span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;

