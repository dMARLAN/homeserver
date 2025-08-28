"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";

export default function NavBar() {
  const pathname = usePathname();
  
  return (
    <nav className="w-full border-b bg-white relative z-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 100 100" className="flex-shrink-0">
              <rect x="4" y="4" width="92" height="92" stroke="currentColor" strokeWidth="5" fill="none"/>
              <text x="50" y="55" fontSize="60" textAnchor="middle" dominantBaseline="middle" fontFamily="sans-serif" fill="currentColor">MP</text>
            </svg>
            <span className="text-xl font-semibold tracking-wider">MARLAN PHOTOGRAPHY</span>
          </div>
          
          <div className="flex items-center h-full">
            <Link href="/" className="h-full">
              <Button 
                variant="ghost"
                className={`text-base h-full rounded-none border-b-2 ${
                  pathname === "/" ? "border-black" : "border-transparent"
                }`}
              >
                HOME
              </Button>
            </Link>
            <Link href="/contact" className="h-full">
              <Button 
                variant="ghost"
                className={`text-base h-full rounded-none border-b-2 ${
                  pathname === "/contact" ? "border-black" : "border-transparent"
                }`}
              >
                CONTACT
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}