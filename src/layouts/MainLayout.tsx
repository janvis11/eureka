import { Outlet } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

const MainLayout = () => (
  <div className="bg-black text-white min-h-screen">
    <Navbar />
    <main className="relative z-10">
      <Outlet />
    </main>
    <Footer />
  </div>
);

export default MainLayout;

