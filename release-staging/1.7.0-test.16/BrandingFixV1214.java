import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.jar.*;
import jdk.internal.org.objectweb.asm.*;
import jdk.internal.org.objectweb.asm.tree.*;

public class BrandingFixV1214 {
    private static final String OWNER = "sgp/client/branding/SgpClientBranding";
    private static final String CLASS = OWNER + ".class";
    private static final String TOML = "META-INF/neoforge.mods.toml";
    private static final String DRAW = "(Lnet/minecraft/client/gui/Font;Ljava/lang/String;IIIZ)I";

    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("usage: BrandingFixV1214 <branding-1.2.13.jar> <out.jar>");
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
            throw new IllegalStateException("unexpected Branding 1.2.13 layout");

        String toml=new String(entries.get(TOML),StandardCharsets.UTF_8);
        if(!toml.contains("version=\"1.2.13\""))
            throw new IllegalStateException("expected Branding 1.2.13");
        toml=toml.replace("version=\"1.2.13\"","version=\"1.2.14\"")
            .replace("dynamic content-width plaque with right padding",
                     "dynamic content-width plaque with centered update-state content");
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

        // Keep normal state 1:1. Only update-state is vertically centered.
        // Cube spans y=12..36, visual center=24.
        // Two text lines (Minecraft font ~9px high) become y=12 and y=28,
        // which centers the two-line block around the same axis.
        int movedTop=0, movedBottom=0, normalUntouched=0;
        for(AbstractInsnNode n=m.instructions.getFirst();n!=null;n=n.getNext()) {
            if(n instanceof MethodInsnNode mi
                && mi.getOpcode()==Opcodes.INVOKEVIRTUAL
                && mi.owner.equals("net/minecraft/client/gui/GuiGraphics")
                && mi.name.equals("drawString")
                && mi.desc.equals(DRAW)) {
                AbstractInsnNode shadow=prevReal(n);
                AbstractInsnNode color=prevReal(shadow);
                AbstractInsnNode y=prevReal(color);
                AbstractInsnNode x=prevReal(y);
                if(intValue(x)==41) {
                    int yv=intValue(y);
                    if(yv==9) {
                        m.instructions.set(y,intInsn(12));
                        movedTop++;
                    } else if(yv==25) {
                        m.instructions.set(y,intInsn(28));
                        movedBottom++;
                    } else if(yv==19) {
                        normalUntouched++;
                    }
                }
            }
        }
        if(movedTop!=1 || movedBottom!=1 || normalUntouched!=1)
            throw new IllegalStateException("unexpected text layout top="+movedTop+" bottom="+movedBottom+" normal="+normalUntouched);

        // Center update button vertically relative to the same y=24 axis.
        // Button height is 20, so y=14 gives center y=24.
        MethodInsnNode setY=null;
        for(AbstractInsnNode n=m.instructions.getFirst();n!=null;n=n.getNext()) {
            if(n instanceof MethodInsnNode mi
                && mi.getOpcode()==Opcodes.INVOKEVIRTUAL
                && mi.owner.equals("net/minecraft/client/gui/components/Button")
                && mi.name.equals("setY")
                && mi.desc.equals("(I)V")) {
                if(setY!=null) throw new IllegalStateException("multiple Button.setY calls");
                setY=mi;
            }
        }
        if(setY==null) throw new IllegalStateException("Button.setY not found");
        AbstractInsnNode by=prevReal(setY);
        if(intValue(by)!=12) throw new IllegalStateException("expected button y=12, got "+intValue(by));
        m.instructions.set(by,intInsn(14));

        ClassWriter cw=new SafeClassWriter(ClassWriter.COMPUTE_FRAMES|ClassWriter.COMPUTE_MAXS);
        cn.accept(cw);
        return cw.toByteArray();
    }

    static AbstractInsnNode prevReal(AbstractInsnNode n){
        n=n.getPrevious();
        while(n!=null && (n.getType()==AbstractInsnNode.LABEL || n.getType()==AbstractInsnNode.LINE || n.getType()==AbstractInsnNode.FRAME))
            n=n.getPrevious();
        return n;
    }

    static int intValue(AbstractInsnNode n){
        int op=n.getOpcode();
        if(op==Opcodes.ICONST_M1) return -1;
        if(op>=Opcodes.ICONST_0 && op<=Opcodes.ICONST_5) return op-Opcodes.ICONST_0;
        if(n instanceof IntInsnNode ii) return ii.operand;
        if(n instanceof LdcInsnNode ldc && ldc.cst instanceof Integer i) return i;
        return Integer.MIN_VALUE;
    }

    static AbstractInsnNode intInsn(int v){
        if(v==-1)return new InsnNode(Opcodes.ICONST_M1);
        if(v>=0&&v<=5)return new InsnNode(Opcodes.ICONST_0+v);
        if(v>=Byte.MIN_VALUE&&v<=Byte.MAX_VALUE)return new IntInsnNode(Opcodes.BIPUSH,v);
        if(v>=Short.MIN_VALUE&&v<=Short.MAX_VALUE)return new IntInsnNode(Opcodes.SIPUSH,v);
        return new LdcInsnNode(v);
    }

    static final class SafeClassWriter extends ClassWriter {
        SafeClassWriter(int f){super(f);}
        @Override protected String getCommonSuperClass(String a,String b){return "java/lang/Object";}
    }
}
