import type { Metadata } from 'next';
import AuthGuard from '@/components/AuthGuard';
import './globals.css';

export const metadata: Metadata = {
  title: 'N-Tier Supply Chain Intelligence',
  description: 'Supply chain risk analysis platform',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-[#0a0a0b] text-white selection:bg-blue-500/30">
        <AuthGuard>{children}</AuthGuard>
      </body>
    </html>
  );
}
