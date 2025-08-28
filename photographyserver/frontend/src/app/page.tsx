"use client";

import { useState } from "react";
import Carousel, { TOTAL_CARDS, CARDS_PER_VIEW, CARD_GRADIENTS } from "@/components/Carousel";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";

export default function Home() {
  const [selectedCard, setSelectedCard] = useState(0);

  const nextCard = () => {
    setSelectedCard((prev) => Math.min(prev + 1, TOTAL_CARDS - 1));
  };

  const prevCard = () => {
    setSelectedCard((prev) => Math.max(prev - 1, 0));
  };

  return (
    <div className="min-h-screen relative">
      {/* Background gradient */}
      <div className={`fixed inset-0 bg-gradient-to-br ${CARD_GRADIENTS[selectedCard]} z-0 transition-all duration-700 ease-in-out`} />
      
      {/* Overlay pattern for texture */}
      <div className="fixed inset-0 opacity-30 pointer-events-none z-0">
        <div className="absolute inset-0 bg-black/20" />
        <div className="absolute inset-0" style={{
          backgroundImage: `repeating-linear-gradient(45deg, transparent, transparent 35px, rgba(255,255,255,.05) 35px, rgba(255,255,255,.05) 70px)`,
        }} />
      </div>
      
      {/* Content */}
      <div className="relative z-10 min-h-screen flex flex-col justify-center py-12">
        <div className="container mx-auto px-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="space-y-6">
            <p className="text-xl text-white/80 leading-relaxed">
              Every photograph tells a story.
            </p>
            <h1 className="text-5xl font-bold tracking-tight text-white">
              Capturing Moments
            </h1>
            <p className="text-sm text-white/60">
              From landscapes to portraits, discover the art of visual storytelling.
            </p>
          </div>
          <div>
            <Carousel selectedCard={selectedCard} />
          </div>
        </div>
        
        <div className="relative flex items-center mt-12">
          <div className="absolute left-1/2 -translate-x-1/2 flex items-center gap-6">
            <Button
              variant="outline"
              size="lg"
              className="rounded-full w-16 h-16 bg-white/10 border-white/20 text-white hover:bg-white/20"
              onClick={prevCard}
              disabled={selectedCard === 0}
            >
              <ChevronLeft className="h-8 w-8" />
            </Button>

            <Button
              variant="outline"
              size="lg"
              className="rounded-full w-16 h-16 bg-white/10 border-white/20 text-white hover:bg-white/20"
              onClick={nextCard}
              disabled={selectedCard === TOTAL_CARDS - 1}
            >
              <ChevronRight className="h-8 w-8" />
            </Button>
          </div>
          
          <div className="w-full flex items-center justify-end">
            <div className="w-1/2 flex items-center pl-24">
              <div className="flex-1 h-2 bg-white/20 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-white transition-all duration-300 ease-out"
                  style={{ 
                    width: `${((selectedCard + 1) / TOTAL_CARDS) * 100}%` 
                  }}
                />
              </div>
              
              <div className="ml-8 text-2xl font-bold text-white">
                {String(selectedCard + 1).padStart(2, '0')}
              </div>
            </div>
          </div>
        </div>
        </div>
      </div>
    </div>
  );
}
