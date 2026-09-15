# Pane Resize + Composer Cap 000024H1

000024 built successfully, but its runtime probe exposed two real CSS issues.

## 1. Manual pane width was still being compressed

The pane host still had:

```css
flex-shrink: 1;
```

so a manual request for 850px could be reduced by the flex algorithm. The Evidence
showed 850px becoming 828px and subsequent 600px/reset checks remaining around 848px.

H1 changes the host to:

```css
flex-shrink: 0;
```

This makes the contract literal:

- normal default/minimum = 600px
- manual 850px = 850px
- manual values below 600px clamp at 600px
- priority minimum = 1200px
- narrow workspaces scroll instead of crushing panes

## 2. Textarea max-height was content-box, not actual rendered height

The Shadow DOM component did not inherit the document-level universal
`box-sizing: border-box`. Therefore `max-height:72px` applied only to the content box,
and padding/border produced a rendered 92px textarea.

H1 adds:

```css
textarea {
  box-sizing: border-box;
}
```

so the rendered textarea itself is capped at 72px.

The original 000024 verifier is intentionally re-run unchanged.
