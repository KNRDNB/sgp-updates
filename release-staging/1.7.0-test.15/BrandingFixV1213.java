import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.jar.*;
import jdk.internal.org.objectweb.asm.*;
import jdk.internal.org.objectweb.asm.tree.*;

public class BrandingFixV1213 {
    private static final String OWNER = "sgp/client/branding/SgpClientBranding";
    private static final String CLASS = OWNER + ".class";
    private static final String TOML = "META-INF/neoforge.mods.toml";
    private static final String FONT = "net/minecraft/client/gui/Font";
    private static final String MINECRAFT = "net/minecraft/client/Minecraft";

    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("usage: BrandingFixV1213 <branding-1.2.12.jar> <out.jar>");
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
            throw new IllegalStateException("unexpected Branding 1.2.12 layout");

        String toml=new String(entries.get(TOML),StandardCharsets.UTF_8);
        if(!toml.contains("version=\"1.2.12\""))
            throw new IllegalStateException("expected Branding 1.2.12");
        toml=toml.replace("version=\"1.2.12\"","version=\"1.2.13\"")
            .replace("right padding", "dynamic content-width plaque with right padding");
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

        if(cn.methods.stream().anyMatch(x->x.name.equals("computePlaqueRight")))
            throw new IllegalStateException("computePlaqueRight already exists");

        MethodNode m=cn.methods.stream()
            .filter(x->x.name.equals("onScreenRenderPost")
                && x.desc.equals("(Lnet/neoforged/neoforge/client/event/ScreenEvent$Render$Post;)V"))
            .findFirst().orElseThrow();

        // Add helper first; it uses the exact text that the renderer already displays.
        cn.methods.add(makePlaqueRightHelper());

        // Reuse local 12 (previous method used 0..11). Compute right edge once per frame:
        // textX + max(visible text widths) + 8px right padding.
        VarInsnNode anchor=null;
        for(AbstractInsnNode n=m.instructions.getFirst(); n!=null; n=n.getNext()) {
            if(n instanceof VarInsnNode vi && vi.getOpcode()==Opcodes.ASTORE && vi.var==7) {
                anchor=vi; break;
            }
        }
        if(anchor==null) throw new IllegalStateException("updateButton ASTORE 7 not found");

        InsnList calc=new InsnList();
        calc.add(new VarInsnNode(Opcodes.ALOAD,2));
        calc.add(new FieldInsnNode(Opcodes.GETFIELD,MINECRAFT,"font","Lnet/minecraft/client/gui/Font;"));
        calc.add(new VarInsnNode(Opcodes.ILOAD,6));
        calc.add(new VarInsnNode(Opcodes.ALOAD,5));
        calc.add(new VarInsnNode(Opcodes.ALOAD,8));
        calc.add(new MethodInsnNode(Opcodes.INVOKESTATIC,OWNER,"computePlaqueRight",
            "(Lnet/minecraft/client/gui/Font;ZLjava/lang/String;Ljava/lang/String;)I",false));
        calc.add(new VarInsnNode(Opcodes.ISTORE,12));
        m.instructions.insert(anchor,calc);

        // Button follows plaque exactly like before: x = plaqueRight + 4, still clamped
        // by the existing Math.min(... guiWidth-88) / Math.max(4, ...) logic.
        AbstractInsnNode buttonConst=null;
        for(AbstractInsnNode n=m.instructions.getFirst(); n!=null; n=n.getNext()) {
            if(intValue(n)==224) { buttonConst=n; break; }
        }
        if(buttonConst==null) throw new IllegalStateException("button x constant 224 not found");
        InsnList buttonX=new InsnList();
        buttonX.add(new VarInsnNode(Opcodes.ILOAD,12));
        buttonX.add(new InsnNode(Opcodes.ICONST_4));
        buttonX.add(new InsnNode(Opcodes.IADD));
        m.instructions.insertBefore(buttonConst,buttonX);
        m.instructions.remove(buttonConst);

        // Replace fixed test.14 plaque right edge 175/174 with dynamic local 12.
        int c175=0, c174=0;
        for(AbstractInsnNode n=m.instructions.getFirst(); n!=null;) {
            AbstractInsnNode next=n.getNext();
            int v=intValue(n);
            if(v==175 && c175<4) {
                m.instructions.set(n,new VarInsnNode(Opcodes.ILOAD,12));
                c175++;
            } else if(v==174 && c174<1) {
                InsnList rightBorder=new InsnList();
                rightBorder.add(new VarInsnNode(Opcodes.ILOAD,12));
                rightBorder.add(new InsnNode(Opcodes.ICONST_1));
                rightBorder.add(new InsnNode(Opcodes.ISUB));
                m.instructions.insertBefore(n,rightBorder);
                m.instructions.remove(n);
                c174++;
            }
            n=next;
        }
        if(c175!=4 || c174!=1)
            throw new IllegalStateException("unexpected test.14 plaque constants 175="+c175+" 174="+c174);

        ClassWriter cw=new SafeClassWriter(ClassWriter.COMPUTE_FRAMES|ClassWriter.COMPUTE_MAXS);
        cn.accept(cw);
        return cw.toByteArray();
    }

    static MethodNode makePlaqueRightHelper() {
        MethodNode m=new MethodNode(Opcodes.ACC_PRIVATE|Opcodes.ACC_STATIC,
            "computePlaqueRight",
            "(Lnet/minecraft/client/gui/Font;ZLjava/lang/String;Ljava/lang/String;)I",
            null,null);
        InsnList i=m.instructions;
        LabelNode normal=new LabelNode();
        LabelNode knownPack=new LabelNode();
        LabelNode afterPack=new LabelNode();

        // if (!update) goto normal
        i.add(new VarInsnNode(Opcodes.ILOAD,1));
        i.add(new JumpInsnNode(Opcodes.IFEQ,normal));

        // update width = max(font.width("Доступно обновление"),
        //                    font.width("Новая версия: " + latest))
        i.add(new VarInsnNode(Opcodes.ALOAD,0));
        i.add(new LdcInsnNode("Доступно обновление"));
        i.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL,FONT,"width","(Ljava/lang/String;)I",false));
        i.add(new VarInsnNode(Opcodes.ISTORE,4));

        i.add(new VarInsnNode(Opcodes.ALOAD,0));
        i.add(new LdcInsnNode("Новая версия: "));
        i.add(new VarInsnNode(Opcodes.ALOAD,2));
        i.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL,"java/lang/String","concat","(Ljava/lang/String;)Ljava/lang/String;",false));
        i.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL,FONT,"width","(Ljava/lang/String;)I",false));
        i.add(new VarInsnNode(Opcodes.ISTORE,5));

        i.add(new VarInsnNode(Opcodes.ILOAD,4));
        i.add(new VarInsnNode(Opcodes.ILOAD,5));
        i.add(new MethodInsnNode(Opcodes.INVOKESTATIC,"java/lang/Math","max","(II)I",false));
        i.add(new IntInsnNode(Opcodes.BIPUSH,41)); // text x
        i.add(new InsnNode(Opcodes.IADD));
        i.add(new IntInsnNode(Opcodes.BIPUSH,8));  // right padding
        i.add(new InsnNode(Opcodes.IADD));
        i.add(new InsnNode(Opcodes.IRETURN));

        // normal line
        i.add(normal);
        i.add(new VarInsnNode(Opcodes.ALOAD,3));
        i.add(new JumpInsnNode(Opcodes.IFNONNULL,knownPack));
        i.add(new LdcInsnNode("Версия SGP: не определена"));
        i.add(new JumpInsnNode(Opcodes.GOTO,afterPack));

        i.add(knownPack);
        i.add(new LdcInsnNode("Версия SGP: "));
        i.add(new VarInsnNode(Opcodes.ALOAD,3));
        i.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL,"java/lang/String","concat","(Ljava/lang/String;)Ljava/lang/String;",false));

        i.add(afterPack);
        i.add(new VarInsnNode(Opcodes.ASTORE,4));
        i.add(new IntInsnNode(Opcodes.BIPUSH,41));
        i.add(new VarInsnNode(Opcodes.ALOAD,0));
        i.add(new VarInsnNode(Opcodes.ALOAD,4));
        i.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL,FONT,"width","(Ljava/lang/String;)I",false));
        i.add(new InsnNode(Opcodes.IADD));
        i.add(new IntInsnNode(Opcodes.BIPUSH,8));
        i.add(new InsnNode(Opcodes.IADD));
        i.add(new InsnNode(Opcodes.IRETURN));

        return m;
    }

    static int intValue(AbstractInsnNode n) {
        int op=n.getOpcode();
        if(op==Opcodes.ICONST_M1) return -1;
        if(op>=Opcodes.ICONST_0 && op<=Opcodes.ICONST_5) return op-Opcodes.ICONST_0;
        if(n instanceof IntInsnNode ii) return ii.operand;
        if(n instanceof LdcInsnNode ldc && ldc.cst instanceof Integer x) return x;
        return Integer.MIN_VALUE;
    }

    static final class SafeClassWriter extends ClassWriter {
        SafeClassWriter(int f){ super(f); }
        @Override protected String getCommonSuperClass(String a,String b){ return "java/lang/Object"; }
    }
}
