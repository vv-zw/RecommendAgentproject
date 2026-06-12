import React from 'react';
import Header from './Header';
import Footer from './Footer';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />
      <main className="flex-1 container mx-auto overflow-x-hidden px-3 py-5 sm:px-4 sm:py-8">
        {children}
      </main>
      <Footer />
    </div>
  );
};

export default Layout;
