"use client";

import { useEffect, useRef } from "react";
import { useReducedMotionSafe } from "@/lib/motion";

const VERT = "attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}";
const FRAG = `
precision mediump float;
uniform vec2 u_res;uniform float u_t;uniform vec2 u_m;
float h(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float n(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);return mix(mix(h(i),h(i+vec2(1,0)),f.x),mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x),f.y);}
float fbm(vec2 p){float v=0.,a=.5;for(int i=0;i<5;i++){v+=a*n(p);p=p*2.02+vec2(3.1,1.7);a*=.5;}return v;}
void main(){
  vec2 uv=gl_FragCoord.xy/u_res;vec2 p=(uv-.5)*vec2(u_res.x/u_res.y,1.);
  float t=u_t*.07;
  vec2 q=vec2(fbm(p*2.+t),fbm(p*2.+vec2(5.2,1.3)-t));
  float f=fbm(p*2.4+q*1.9+vec2(t*2.,-t));
  vec2 m=(u_m-.5)*vec2(u_res.x/u_res.y,1.);
  float pool=exp(-dot(p-m,p-m)*6.);
  vec3 rose=vec3(.93,.2,.2),amber=vec3(1.,.66,.18),teal=vec3(.0,.6,.74);
  vec3 col=mix(mix(rose,amber,smoothstep(.25,.72,f)),teal,smoothstep(.5,.95,q.x));
  float a=(smoothstep(.38,.88,f)*.5+pool*.55)*smoothstep(1.15,.15,length(p));
  gl_FragColor=vec4(col*a,a);
}`;

/**
 * A field of living light drawn on the graphics card: slow, warped colour that pools toward the
 * pointer. It sits over a film with a screen blend. It draws only while on screen, at half resolution,
 * and a single still frame for anyone who prefers less motion.
 */
export function LightField({
  className,
  follow = true,
}: {
  className?: string;
  follow?: boolean;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const { reduced } = useReducedMotionSafe();

  useEffect(() => {
    const canvas = ref.current;
    const gl = canvas?.getContext("webgl", {
      alpha: true,
      premultipliedAlpha: true,
      antialias: false,
    });
    if (!canvas || !gl) return;
    const compile = (type: number, src: string) => {
      const s = gl.createShader(type)!;
      gl.shaderSource(s, src);
      gl.compileShader(s);
      return s;
    };
    const prog = gl.createProgram()!;
    gl.attachShader(prog, compile(gl.VERTEX_SHADER, VERT));
    gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, FRAG));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return;
    gl.useProgram(prog);
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 3, -1, -1, 3]),
      gl.STATIC_DRAW,
    );
    const loc = gl.getAttribLocation(prog, "p");
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    const uRes = gl.getUniformLocation(prog, "u_res");
    const uT = gl.getUniformLocation(prog, "u_t");
    const uM = gl.getUniformLocation(prog, "u_m");

    const mouse = { x: 0.7, y: 0.5, tx: 0.7, ty: 0.5 };
    let raf = 0;
    let visible = true;
    const start = performance.now();
    const size = () => {
      canvas.width = Math.max(2, Math.floor(canvas.clientWidth / 2));
      canvas.height = Math.max(2, Math.floor(canvas.clientHeight / 2));
      gl.viewport(0, 0, canvas.width, canvas.height);
    };
    const draw = (now: number) => {
      mouse.x += (mouse.tx - mouse.x) * 0.05;
      mouse.y += (mouse.ty - mouse.y) * 0.05;
      gl.uniform2f(uRes, canvas.width, canvas.height);
      gl.uniform1f(uT, reduced ? 12 : (now - start) / 1000);
      gl.uniform2f(uM, mouse.x, mouse.y);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      if (!reduced && visible) raf = requestAnimationFrame(draw);
    };
    const onMove = (e: PointerEvent) => {
      const r = canvas.getBoundingClientRect();
      mouse.tx = (e.clientX - r.left) / r.width;
      mouse.ty = 1 - (e.clientY - r.top) / r.height;
    };
    size();
    draw(performance.now());
    const io = new IntersectionObserver(([e]) => {
      visible = e.isIntersecting;
      if (visible && !reduced) raf = requestAnimationFrame(draw);
    });
    io.observe(canvas);
    window.addEventListener("resize", size);
    if (follow) window.addEventListener("pointermove", onMove);
    return () => {
      cancelAnimationFrame(raf);
      io.disconnect();
      window.removeEventListener("resize", size);
      window.removeEventListener("pointermove", onMove);
    };
  }, [reduced, follow]);

  return <canvas ref={ref} aria-hidden className={className} />;
}
