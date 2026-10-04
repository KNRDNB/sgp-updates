import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.jar.*;
import jdk.internal.org.objectweb.asm.*;
import jdk.internal.org.objectweb.asm.tree.*;

public class BrandingFixV1212 {
    private static final String OWNER = "sgp/client/branding/SgpClientBranding";
    private static final String CLASS = OWNER + ".class";
    private static final String TOML = "META-INF/neoforge.mods.toml";

    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("usage: BrandingFixV1212 <branding-1.2.11.jar> <out.jar>");
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
            throw new IllegalStateException("unexpected Branding 1.2.11 layout");

        String toml=new String(entries.get(TOML),StandardCharsets.UTF_8);
        if(!toml.contains("version=\"1.2.11\""))
            throw new IllegalStateException("expected Branding 1.2.11");
        toml=toml.replace("version=\"1.2.11\"","version=\"1.2.12\"")
            .replace("restored full test.5 cube bounds and compact plaque width",
                     "restored full test.5 cube bounds and compact plaque width with right padding");
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

        // test.13 geometry is accepted except for the right edge being too close
        // to the version text. Add exactly 6 GUI px of right padding:
        // background/top/bottom right = 169 -> 175
        // right border start = 168 -> 174
        int c169=0, c168=0;
        for(AbstractInsnNode n=m.instructions.getFirst(); n!=null;) {
            AbstractInsnNode next=n.getNext();
            int v=intValue(n);
            if(v==169 && c169<4) {
                m.instructions.set(n,intInsn(175));
                c169++;
            } else if(v==168 && c168<1) {
                m.instructions.set(n,intInsn(174));
                c168++;
            }
            n=next;
        }
        if(c169!=4 || c168!=1)
            throw new IllegalStateException("unexpected test.13 plaque constants 169="+c169+" 168="+c168);

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
        if(v==-1)return new InsnNode(Opcodes.ICONST_M1);
        if(v>=0&&v<=5)return new InsnNode(Opcodes.ICONST_0+v);
        if(v>=Byte.MIN_VALUE&&v<=Byte.MAX_VALUE)return new IntInsnNode(Opcodes.BIPUSH,v);
        if(v>=Short.MIN_VALUE&&v<=Short.MAX_VALUE)return new IntInsnNode(Opcodes.SIPUSH,v);
        return new LdcInsnNode(v);
    }

    static final class SafeClassWriter extends ClassWriter {
        SafeClassWriter(int f){ super(f); }
        @Override protected String getCommonSuperClass(String a,String b){ return "java/lang/Object"; }
    }
}
