import { createI18nMiddleware } from "fumadocs-core/i18n/middleware";
import { isMarkdownPreferred, rewritePath } from "fumadocs-core/negotiation";
import { type NextProxy, NextResponse } from "next/server";

import { i18n } from "@/lib/i18n";
import { docsContentRoute, docsRoute } from "@/lib/shared";

const i18nMiddleware = createI18nMiddleware(i18n);

const { rewrite: rewriteDocs } = rewritePath(
  `${docsRoute}{/*path}`,
  `${docsContentRoute}{/*path}/content.md`,
);
const { rewrite: rewriteSuffix } = rewritePath(
  `${docsRoute}{/*path}.md`,
  `${docsContentRoute}{/*path}/content.md`,
);

function stripLangPrefix(pathname: string): string {
  const match = pathname.match(/^\/([^/]+)(\/.*)?$/);
  if (match && (i18n.languages as readonly string[]).includes(match[1])) {
    return match[2] ?? "/";
  }
  return pathname;
}

const proxy: NextProxy = (request, event) => {
  const stripped = stripLangPrefix(request.nextUrl.pathname);

  if (stripped !== request.nextUrl.pathname && stripped.startsWith(`${docsContentRoute}/`)) {
    return NextResponse.rewrite(new URL(stripped, request.nextUrl));
  }

  const result = rewriteSuffix(stripped);
  if (result) {
    return NextResponse.rewrite(new URL(result, request.nextUrl));
  }

  if (isMarkdownPreferred(request)) {
    const result = rewriteDocs(stripped);
    if (result) {
      return NextResponse.rewrite(new URL(result, request.nextUrl));
    }
  }

  return i18nMiddleware(request, event);
};

export default proxy;

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
