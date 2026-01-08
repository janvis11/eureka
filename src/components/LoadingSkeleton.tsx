export const CardSkeleton = () => (
  <div className="border border-black/10 rounded-3xl p-6 space-y-4 animate-pulse">
    <div className="h-6 bg-gray-200 rounded w-3/4"></div>
    <div className="h-4 bg-gray-200 rounded w-full"></div>
    <div className="h-4 bg-gray-200 rounded w-5/6"></div>
  </div>
);

export const StatCardSkeleton = () => (
  <div className="border border-white/10 rounded-3xl p-6 space-y-2 bg-white/5 animate-pulse">
    <div className="h-4 bg-white/20 rounded w-1/2"></div>
    <div className="h-12 bg-white/20 rounded w-3/4"></div>
    <div className="h-3 bg-white/20 rounded w-full"></div>
  </div>
);

export const MessageSkeleton = () => (
  <div className="space-y-2 animate-pulse">
    <div className="flex items-center space-x-3">
      <div className="h-4 bg-white/20 rounded w-16"></div>
      <div className="h-3 bg-white/10 rounded w-20"></div>
    </div>
    <div className="h-4 bg-white/20 rounded w-full"></div>
    <div className="h-4 bg-white/20 rounded w-5/6"></div>
  </div>
);

