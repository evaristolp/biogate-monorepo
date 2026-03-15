import type { Metadata, Viewport } from 'next'
import { Fraunces, Inter, JetBrains_Mono } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import './globals.css'

const fraunces = Fraunces({
  subsets: ['latin'],
  variable: '--font-display',
  weight: 'variable',
  style: ['normal', 'italic'],
  axes: ['WONK', 'opsz'],
})

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  weight: ['300', '400', '500', '600'],
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  weight: ['400', '500'],
})

export const viewport: Viewport = {
  themeColor: '#090909',
}

export const metadata: Metadata = {
  title: 'BioGate — BIOSECURE Act Intelligence',
  description:
    'Pre-audit intelligence for BIOSECURE Act compliance. Screen your vendor supply chain against federal watchlists in minutes, not weeks.',
  icons: {
    icon: { url: '/icon.svg', type: 'image/svg+xml' },
  },
}

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body
        suppressHydrationWarning
        className={`${fraunces.variable} ${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}
      >
        {children}
        <Analytics />
      </body>
    </html>
  )
}
