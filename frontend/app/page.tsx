import { Hero } from "@/components/hero";
import { SearchForm } from "@/components/search-form";

export default function HomePage() {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center px-5 py-16 sm:px-8 sm:py-24">
      <Hero>
        <div className="rounded-2xl border border-border/80 bg-card p-5 shadow-sm sm:p-7">
          <SearchForm />
        </div>
      </Hero>
    </div>
  );
}
