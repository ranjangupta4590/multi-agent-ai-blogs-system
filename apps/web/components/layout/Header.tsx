"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import ActiveProviderBadge from "@/components/layout/ActiveProviderBadge";
import ThemeToggle from "@/components/layout/ThemeToggle";
import { api } from "@/lib/api";
import { Article, Claim, Project, User } from "@/lib/types";

type HeaderProps = { onOpenMobileMenu: () => void };
type SearchResult = { id: string; type: "Project" | "Article" | "Claim"; title: string; subtitle: string; href: string; searchText: string };

export default function Header({ onOpenMobileMenu }: HeaderProps) {
  const router = useRouter();
  const searchLoaded = useRef(false);
  const [user, setUser] = useState<User | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [searchIndex, setSearchIndex] = useState<SearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [activeResult, setActiveResult] = useState(0);

  useEffect(() => { api.getMe().then(setUser).catch(() => setUser(null)); }, []);

  const buildSearchIndex = async () => {
    if (searchLoaded.current || searchLoading) return;
    setSearchLoading(true);
    try {
      const projects = await api.getProjects();
      const articleGroups = await Promise.all(projects.map((project: Project) => api.getArticles(project.id).catch(() => [])));
      const articles = articleGroups.flat() as Article[];
      const claimGroups = await Promise.all(articles.map((article) => api.getClaims(article.id).catch(() => [])));
      const articleById = new Map(articles.map((article) => [article.id, article]));
      const projectResults: SearchResult[] = projects.map((project: Project) => ({ id: project.id, type: "Project", title: project.name, subtitle: project.industry || "Project", href: "/projects", searchText: `${project.name} ${project.description || ""} ${project.industry || ""}` }));
      const articleResults: SearchResult[] = articles.map((article) => ({ id: article.id, type: "Article", title: article.title, subtitle: `${article.status.replace("_", " ")} · ${article.word_count} words`, href: `/articles/${article.id}`, searchText: `${article.title} ${article.topic} ${article.summary || ""} ${article.target_keywords.join(" ")}` }));
      const claimResults: SearchResult[] = claimGroups.flat().map((claim: Claim) => {
        const article = articleById.get(claim.article_id);
        return { id: claim.id, type: "Claim", title: claim.claim_text, subtitle: article ? `Claim in ${article.title}` : "Article claim", href: article ? `/articles/${article.id}` : "/sources", searchText: `${claim.claim_text} ${claim.notes || ""} ${article?.title || ""}` };
      });
      setSearchIndex([...projectResults, ...articleResults, ...claimResults]);
      searchLoaded.current = true;
    } finally { setSearchLoading(false); }
  };

  const results = query.trim().length < 2 ? [] : searchIndex.filter((item) => item.searchText.toLowerCase().includes(query.trim().toLowerCase())).slice(0, 8);
  const chooseResult = (result: SearchResult) => { setQuery(""); setSearchOpen(false); router.push(result.href); };
  const logout = async () => { try { await api.logout(); } catch { /* Local cleanup still signs the user out safely. */ } localStorage.removeItem("token"); setProfileOpen(false); router.replace("/login"); };
  const handleSearchKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") { setSearchOpen(false); return; }
    if (!results.length) return;
    if (event.key === "ArrowDown") { event.preventDefault(); setActiveResult((current) => (current + 1) % results.length); }
    if (event.key === "ArrowUp") { event.preventDefault(); setActiveResult((current) => (current - 1 + results.length) % results.length); }
    if (event.key === "Enter") { event.preventDefault(); chooseResult(results[activeResult]); }
  };

  return (
    <header className="app-header">
      <div className="header-left">
        <button className="mobile-menu-button" onClick={onOpenMobileMenu} aria-label="Open navigation">☰</button>
        <div className="header-search-wrap">
          <label className="header-search">
            <span aria-hidden="true">⌕</span>
            <input value={query} onChange={(event) => { setQuery(event.target.value); setActiveResult(0); }} onFocus={() => { setSearchOpen(true); buildSearchIndex(); }} onKeyDown={handleSearchKeyDown} type="search" placeholder="Search articles, projects, claims..." aria-label="Search articles, projects, and claims" aria-expanded={searchOpen} aria-controls="global-search-results" />

          </label>
          {searchOpen && (searchLoading || query.trim().length >= 2) && <div id="global-search-results" className="search-results" role="listbox">
            {searchLoading ? <p className="search-state">Preparing your searchable workspace…</p> : results.length === 0 ? <p className="search-state">No matching workspace items found.</p> : results.map((result, index) => <button key={`${result.type}-${result.id}`} className={`search-result ${index === activeResult ? "is-active" : ""}`} onMouseDown={(event) => event.preventDefault()} onClick={() => chooseResult(result)} role="option" aria-selected={index === activeResult}><span className={`search-result-type type-${result.type.toLowerCase()}`}>{result.type}</span><span><strong>{result.title}</strong><small>{result.subtitle}</small></span><i>→</i></button>)}
          </div>}
        </div>
      </div>

      <div className="header-actions">
        <ActiveProviderBadge /><div className="header-divider" /><div className="header-theme"><ThemeToggle /></div>
        {user ? <div className="profile-menu-wrap"><button className="header-profile" onClick={() => setProfileOpen((open) => !open)} aria-expanded={profileOpen} aria-label="Open account menu" title={`${user.full_name} · ${user.role}`}><span className="profile-avatar">{user.full_name.charAt(0).toUpperCase()}</span><span className="profile-copy"><strong>{user.full_name}</strong><small>{user.role}</small></span><span className="profile-chevron" aria-hidden="true">⌄</span></button>{profileOpen && <div className="profile-popover"><div className="profile-popover-identity"><strong>{user.full_name}</strong><small>{user.role}</small></div><div className="profile-mobile-theme"><ThemeToggle /></div><button className="profile-logout" onClick={logout}><span aria-hidden="true">↪</span> Log out</button></div>}</div> : <Link href="/login" className="btn btn-primary header-signin">Sign in</Link>}
      </div>
    </header>
  );
}
