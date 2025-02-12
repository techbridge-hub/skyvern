import { Link, Outlet } from "react-router-dom";
import { Toaster } from "@/components/ui/toaster";
import { SideNav } from "./SideNav";
import { DiscordLogoIcon } from "@radix-ui/react-icons";
import { Logo } from "@/components/Logo";
import { Profile } from "./Profile";
import { useContext } from "react";
import { UserContext } from "@/store/UserContext";
import GitHubButton from "react-github-btn";

function RootLayout() {
  const user = useContext(UserContext);

  return (
    <>
      <div className="h-full w-full px-4">
        <aside className="fixed min-h-screen w-72 shrink-0 border-r-2 px-6">
          <Link to={window.location.origin}>
            <div className="h-24">
              <Logo />
            </div>
          </Link>
          <SideNav />
          {user ? (
            <div className="absolute bottom-2 left-0 w-72 shrink-0 px-6">
              <Profile name={user.name} />
            </div>
          ) : null}
        </aside>
        <div className="flex h-24 items-center justify-end gap-4 px-6 pl-72">
          <Link
            to="https://discord.com/invite/fG2XXEuQX3"
            target="_blank"
            rel="noopener noreferrer"
          >
            <DiscordLogoIcon className="h-7 w-7" />
          </Link>
          <div className="h-7">
            <GitHubButton
              href="https://github.com/skyvern-ai/skyvern"
              data-color-scheme="no-preference: dark; light: dark; dark: dark;"
              data-size="large"
              data-show-count="true"
              aria-label="Star skyvern-ai/skyvern on GitHub"
            >
              Star
            </GitHubButton>
          </div>
        </div>
        <main className="pb-4 pl-72">
          <Outlet />
        </main>
      </div>
      <Toaster />
    </>
  );
}

export { RootLayout };
