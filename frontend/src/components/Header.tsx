// src/components/Header.tsx
import { Link } from "react-router-dom";

const Header = () => (
  <header className="w-full border-b border-border">
    <div className="container flex items-center justify-between py-4">
      <Link to="/" className="flex items-center gap-2">
        <svg width="32" height="20" viewBox="0 0 32 20" fill="none" className="text-foreground">
          <path d="M2 10h28M6 6l-4 4 4 4M26 6l4 4-4 4M10 2l6 8-6 8M16 2l6 8-6 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
        <span className="text-lg font-semibold tracking-tight">VeriFlow</span>
      </Link>
      <nav className="flex items-center gap-6 text-sm text-muted-foreground">
        <Link to="/how-it-works" className="hover:text-foreground transition-colors">How it works</Link>
        <Link to="/about" className="hover:text-foreground transition-colors">About</Link>
      </nav>
    </div>
  </header>
);

export default Header;
