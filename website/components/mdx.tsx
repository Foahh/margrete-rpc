import * as Python from "fumadocs-python/components";
import defaultMdxComponents from "fumadocs-ui/mdx";
import type { MDXComponents } from "mdx/types";
import * as TabsComponents from "./ui/tabs";
import * as FileComponents from "./files";
import * as ImageComponents from "./image-zoom";

export function getMDXComponents(components?: MDXComponents) {
  return {
    ...defaultMdxComponents,
    img: (props) => <ImageComponents.ImageZoom {...(props as any)} />,
    ...ImageComponents,
    ...TabsComponents,
    ...FileComponents,
    ...Python,
    ...components,
  } satisfies MDXComponents;
}

export const useMDXComponents = getMDXComponents;

declare global {
  type MDXProvidedComponents = ReturnType<typeof getMDXComponents>;
}
