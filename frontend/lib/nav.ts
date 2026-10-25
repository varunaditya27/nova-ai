import {
  BookOpen,
  CalendarHeart,
  HandHelping,
  HeartHandshake,
  Lock,
  MessageCircle,
  Route,
  Sparkles,
  Sun,
  Users,
  Wrench,
  Bookmark,
  type LucideIcon,
} from "lucide-react";

export type NavItem = {
  href: string;
  label: string;
  /** One plain sentence: what you will find here. Shown in the jump menu. */
  about: string;
  icon: LucideIcon;
};

export type NavGroup = { title: string | null; items: NavItem[] };

export const NAV: NavGroup[] = [
  {
    title: null,
    items: [
      { href: "/", label: "Talk", about: "Your one ongoing conversation with Nova", icon: MessageCircle },
      { href: "/today", label: "Today", about: "What’s on Nova’s mind and what’s coming up", icon: Sun },
    ],
  },
  {
    title: "Together",
    items: [
      { href: "/story", label: "Our story", about: "Your weeks as chapters, your days, your firsts", icon: BookOpen },
      { href: "/keepsakes", label: "Keepsakes", about: "Messages you saved and moments that mattered", icon: Bookmark },
    ],
  },
  {
    title: "About you",
    items: [
      { href: "/memory", label: "Memory", about: "What Nova remembers, and how to make it forget", icon: Sparkles },
      { href: "/people", label: "People", about: "The people in your life Nova has come to know", icon: Users },
      { href: "/goals", label: "Goals", about: "What you’re working toward, and the habits that help", icon: Route },
    ],
  },
  {
    title: "Nova",
    items: [
      { href: "/us", label: "How we talk", about: "How well Nova knows you and how you like to talk", icon: HeartHandshake },
      { href: "/errands", label: "Errands", about: "Things Nova can do for you, with your say-so", icon: HandHelping },
      { href: "/care", label: "Care", about: "Times Nova checked in on you, and who to call", icon: CalendarHeart },
    ],
  },
  {
    title: null,
    items: [
      { href: "/privacy", label: "Privacy", about: "Proof that your data is yours and unaltered", icon: Lock },
      { href: "/upkeep", label: "Upkeep", about: "Nova’s housekeeping — run it by hand", icon: Wrench },
    ],
  },
];

export const ALL_NAV: NavItem[] = NAV.flatMap((g) => g.items);

/** The four things you reach for most; everything else lives behind "More" on a phone. */
export const TABS: NavItem[] = ALL_NAV.filter((i) => ["/", "/today", "/story", "/goals"].includes(i.href));

export function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}
