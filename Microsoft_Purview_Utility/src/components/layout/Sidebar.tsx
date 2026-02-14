import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Search,
  Database,
  FolderTree,
  Package,
  Play,
  BookOpen,
  Shield,
  Settings,
  HelpCircle,
  Library,
  Sparkles,
} from "lucide-react";
import purviewLogo from "@/assets/purview-logo.png";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

const navItems = [
  { icon: Search, label: "Assets", path: "/" },
  { icon: Package, label: "Data Products", path: "/products" },
  { icon: Sparkles, label: "Curate", path: "/curate" },
];

const bottomItems = [
  { icon: HelpCircle, label: "Support", path: "/support" },
  { icon: Settings, label: "Settings", path: "/settings" },
];

export function Sidebar() {
  const location = useLocation();

  return (
    <TooltipProvider delayDuration={0}>
      <aside className="h-screen w-[72px] bg-sidebar flex flex-col border-r border-sidebar-border">
        {/* Logo */}
        <NavLink
          to="/"
          className="flex items-center justify-center py-4 border-b border-sidebar-border hover:bg-sidebar-accent/30 transition-colors"
        >
          <img
            src={purviewLogo}
            alt="Purview"
            className="w-10 h-10 object-contain"
          />
        </NavLink>

        {/* Main Navigation */}
        <nav className="flex-1 py-3 flex flex-col items-center gap-1 overflow-y-auto custom-scrollbar">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path || 
              (item.path === "/" && location.pathname === "/");
            
            return (
              <Tooltip key={item.path}>
                <TooltipTrigger asChild>
                  <NavLink
                    to={item.path}
                    className={cn(
                      "nav-item w-14",
                      isActive && "active"
                    )}
                  >
                    <item.icon className="w-5 h-5" />
                    <span className="text-[10px] font-medium">{item.label}</span>
                  </NavLink>
                </TooltipTrigger>
                <TooltipContent side="right" className="font-medium">
                  {item.label}
                </TooltipContent>
              </Tooltip>
            );
          })}
        </nav>

        {/* Bottom Navigation */}
        <div className="py-3 flex flex-col items-center gap-1 border-t border-sidebar-border">
          {bottomItems.map((item) => (
            <Tooltip key={item.path}>
              <TooltipTrigger asChild>
                <NavLink
                  to={item.path}
                  className={({ isActive }) =>
                    cn(
                      "nav-item w-14",
                      isActive && "active"
                    )
                  }
                >
                  <item.icon className="w-5 h-5" />
                  <span className="text-[10px] font-medium">{item.label}</span>
                </NavLink>
              </TooltipTrigger>
              <TooltipContent side="right" className="font-medium">
                {item.label}
              </TooltipContent>
            </Tooltip>
          ))}
        </div>
      </aside>
    </TooltipProvider>
  );
}
