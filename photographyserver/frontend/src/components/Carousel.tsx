"use client";

interface CarouselProps {
  selectedCard: number;
}

export const TOTAL_CARDS = 8;
export const CARDS_PER_VIEW = 3.5;

// Different gradient backgrounds for each card
export const CARD_GRADIENTS = [
  'from-slate-900 via-purple-900 to-slate-900',
  'from-gray-700 via-gray-900 to-black',
  'from-rose-900 via-pink-900 to-purple-900',
  'from-blue-900 via-blue-700 to-purple-900',
  'from-emerald-900 via-green-800 to-teal-900',
  'from-orange-900 via-red-900 to-pink-900',
  'from-indigo-900 via-blue-900 to-purple-900',
  'from-yellow-900 via-amber-900 to-orange-900',
];

export default function Carousel({ selectedCard }: CarouselProps) {
  const cardWidthPercent = 100 / CARDS_PER_VIEW;
  
  // Create array of only visible cards (those after the selected card)
  const visibleCards = [...Array(TOTAL_CARDS)]
    .map((_, index) => index)
    .filter(index => index > selectedCard);

  return (
    <div className="w-full">
      <div className="relative overflow-hidden mx-[-1rem] py-4">
        <div className="flex">
          {visibleCards.map((cardIndex) => (
            <div
              key={cardIndex}
              className="flex-shrink-0 px-2 py-2"
              style={{ 
                width: `${cardWidthPercent}%`
              }}
            >
              <div className="rounded-lg aspect-[4/6] shadow-lg relative overflow-hidden">
                {/* Gradient background */}
                <div className={`absolute inset-0 bg-gradient-to-br ${CARD_GRADIENTS[cardIndex]}`} />
                
                {/* Overlay pattern for texture */}
                <div className="absolute inset-0 opacity-30">
                  <div className="absolute inset-0 bg-black/20" />
                  <div className="absolute inset-0" style={{
                    backgroundImage: `repeating-linear-gradient(45deg, transparent, transparent 35px, rgba(255,255,255,.05) 35px, rgba(255,255,255,.05) 70px)`,
                  }} />
                </div>
                
                {/* Text content */}
                <div className="absolute bottom-4 left-4 right-4 z-10">
                  <p className="text-xs text-white/70">Lorem ipsum</p>
                  <h3 className="text-2xl font-bold text-white break-words w-2/3">Dolor Lorem</h3>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
