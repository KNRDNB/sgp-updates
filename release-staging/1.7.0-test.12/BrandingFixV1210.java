import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.jar.*;
import jdk.internal.org.objectweb.asm.*;
import jdk.internal.org.objectweb.asm.tree.*;

public class BrandingFixV1210 {
    private static final String OWNER = "sgp/client/branding/SgpClientBranding";
    private static final String CLASS = OWNER + ".class";
    private static final String TOML = "META-INF/neoforge.mods.toml";

    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("usage: BrandingFixV1210 <branding-1.2.9.jar> <out.jar>");
        Path in=Path.of(args[0]), out=Path.of(args[1]);

        LinkedHashMap<String, byte[]> entries=new LinkedHashMap<>();
        LinkedHashMap<String, JarEntry> meta=new LinkedHashMap<>();
        try (JarFile jf=new JarFile(in.toFile())) {
            Enumeration<JarEntry> en=jf.entries();
            while(en.hasMoreElements()) {
                JarEntry je=en.nextElement();
                if(je.isDirectory()) continue;
                try(InputStream is=jf.getInputStream(je)){ entries.put(je.getName(),is.readAllBytes()); }
                meta.put(je.getName(),je);
            }
        }

        if(!entries.containsKey(CLASS) || !entries.containsKey(TOML))
            throw new IllegalStateException("unexpected Branding 1.2.9 layout");

        String toml=new String(entries.get(TOML),StandardCharsets.UTF_8);
        if(!toml.contains("version=\"1.2.9\""))
            throw new IllegalStateException("expected Branding 1.2.9");
        toml=toml.replace("version=\"1.2.9\"","version=\"1.2.10\"")
            .replace("exact test.5-style scaled cube icon, explicit SGP version label",
                     "exact test.5-style scaled cube icon, compact plaque width, explicit SGP version label");
        entries.put(TOML,toml.getBytes(StandardCharsets.UTF_8));
        entries.put(CLASS,patch(entries.get(CLASS)));

        Files.deleteIfExists(out);
        try(JarOutputStream jos=new JarOutputStream(Files.newOutputStream(out))) {
            for(var e:entries.entrySet()) {
                JarEntry old=meta.get(e.getKey()), ne=new JarEntry(e.getKey());
                if(old!=null && old.getTime()>=0) ne.setTime(old.getTime());
                jos.putNextEntry(ne);
                jos.write(e.getValue());
                jos.closeEntry();
            }
        }
    }

    static byte[] patch(byte[] bytes) {
        ClassNode cn=new ClassNode();
        new ClassReader(bytes).accept(cn,0);
        MethodNode m=cn.methods.stream()
            .filter(x->x.name.equals("onScreenRenderPost")
                && x.desc.equals("(Lnet/neoforged/neoforge/client/event/ScreenEvent$Render$Post;)V"))
            .findFirst().orElseThrow();

        // The test.11 screenshot proved that the cube/text placement is good and only
        // the fixed 220px plaque right edge is too long. Keep all Branding bytes/logic
        // except the five fill() right-edge constants:
        //   background/top/bottom right = 220 -> 164
        //   right border x1/x2 = 219/220 -> 163/164
        int c220=0, c219=0;
        for(AbstractInsnNode n=m.instructions.getFirst(); n!=null; ) {
            AbstractInsnNode next=n.getNext();
            int v=intValue(n);
            if(v==220 && c220<4) {
                m.instructions.set(n,intInsn(164));
                c220++;
            } else if(v==219 && c219<1) {
                m.instructions.set(n,intInsn(163));
                c219++;
            }
            n=next;
        }
        if(c220!=4 || c219!=1)
            throw new IllegalStateException("unexpected plaque constants 220="+c220+" 219="+c219);

        ClassWriter cw=new SafeClassWriter(ClassWriter.COMPUTE_FRAMES|ClassWriter.COMPUTE_MAXS);
        cn.accept(cw);
        return cw.toByteArray();
    }

    static int intValue(AbstractInsnNode n) {
        int op=n.getOpcode();
        if(op==Opcodes.ICONST_M1) return -1;
        if(op>=Opcodes.ICONST_0 && op<=Opcodes.ICONST_5) return op-Opcodes.ICONST_0;
        if(n instanceof IntInsnNode ii) return ii.operand;
        if(n instanceof LdcInsnNode ldc && ldc.cst instanceof Integer i) return i;
        return Integer.MIN_VALUE;
    }

    static AbstractInsnNode intInsn(int v) {
        if(v==-1) return new InsnNode(Opcodes.ICONST_M1);
        if(v>=0 && v<=5) return new InsnNode(Opcodes.ICONST_0+v);
        if(v>=Byte.MIN_VALUE && v<=Byte.MAX_VALUE) return new IntInsnNode(Opcodes.BIPUSH,v);
        if(v>=Short.MIN_VALUE && v<=Short.MAX_VALUE) return new IntInsnNode(Opcodes.SIPUSH,v);
        return new LdcInsnNode(v);
    }

    static final class SafeClassWriter extends ClassWriter {
        SafeClassWriter(int f){ super(f); }
        @Override protected String getCommonSuperClass(String a,String b){ return "java/lang/Object"; }
    }
}
