interface HeaderProps {
  title: string;
  subtitle: string;
}

export default function Header({ title, subtitle }: HeaderProps) {
  return (
    <header className="text-center py-8">
      <div className="flex items-center justify-center gap-4 mb-2">
        <img
          src="/ocelonis-logo.png"
          alt="Ocelonis Logo"
          className="w-12 h-12 md:w-16 md:h-16"
        />
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 via-cyan-500 to-purple-500 animate-gradient">
          {title}
        </h1>
      </div>
      <p className="text-lg md:text-xl text-gray-400 font-mono">{subtitle}</p>
    </header>
  );
}
