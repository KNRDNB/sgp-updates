import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.jar.*;
import jdk.internal.org.objectweb.asm.*;
import jdk.internal.org.objectweb.asm.tree.*;

public class BrandingFixV129 {
    private static final String OWNER = "sgp/client/branding/SgpClientBranding";
    private static final String CLASS = OWNER + ".class";
    private static final String LOGO = "assets/sgp_client_branding/textures/gui/sgp_logo.png";
    private static final String TOML = "META-INF/neoforge.mods.toml";
    private static final String BLIT = "(Lnet/minecraft/resources/ResourceLocation;IIIIFFIIII)V";

    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("usage: BrandingFixV129 <branding-1.2.8.jar> <test5-cube-48x48.png> <out.jar>");
        Path in=Path.of(args[0]), logo=Path.of(args[1]), out=Path.of(args[2]);
        byte[] logoBytes=Files.readAllBytes(logo);
        if (logoBytes.length < 24 || logoBytes[0] != (byte)0x89 || logoBytes[1] != 0x50 || logoBytes[2] != 0x4e || logoBytes[3] != 0x47)
            throw new IllegalStateException("expected PNG logo");
        int logoW=readInt(logoBytes,16), logoH=readInt(logoBytes,20);
        if (logoW != 48 || logoH != 48) throw new IllegalStateException("expected 48x48 test.5 cube source, got "+logoW+"x"+logoH);

        LinkedHashMap<String, byte[]> entries=new LinkedHashMap<>();
        LinkedHashMap<String, JarEntry> meta=new LinkedHashMap<>();
        try (JarFile jf=new JarFile(in.toFile())) {
            Enumeration<JarEntry> en=jf.entries();
            while(en.hasMoreElements()) {
                JarEntry je=en.nextElement(); if(je.isDirectory()) continue;
                try(InputStream is=jf.getInputStream(je)){ entries.put(je.getName(),is.readAllBytes()); }
                meta.put(je.getName(),je);
            }
        }
        if(!entries.containsKey(CLASS) || !entries.containsKey(LOGO) || !entries.containsKey(TOML)) throw new IllegalStateException("unexpected Branding 1.2.8 layout");
        String toml=new String(entries.get(TOML),StandardCharsets.UTF_8);
        if(!toml.contains("version=\"1.2.8\"")) throw new IllegalStateException("expected Branding 1.2.8");
        toml=toml.replace("version=\"1.2.8\"","version=\"1.2.9\"")
            .replace("cube-only 1:1 transparent icon, explicit SGP version label",
                     "exact test.5-style scaled cube icon, explicit SGP version label");
        entries.put(TOML,toml.getBytes(StandardCharsets.UTF_8));
        entries.put(CLASS,patch(entries.get(CLASS)));
        entries.put(LOGO,logoBytes);

        Files.deleteIfExists(out);
        try(JarOutputStream jos=new JarOutputStream(Files.newOutputStream(out))) {
            for(var e:entries.entrySet()) {
                JarEntry old=meta.get(e.getKey()), ne=new JarEntry(e.getKey());
                if(old!=null && old.getTime()>=0) ne.setTime(old.getTime());
                jos.putNextEntry(ne); jos.write(e.getValue()); jos.closeEntry();
            }
        }
    }

    static byte[] patch(byte[] bytes) {
        ClassNode cn=new ClassNode(); new ClassReader(bytes).accept(cn,0);
        MethodNode m=cn.methods.stream()
            .filter(x->x.name.equals("onScreenRenderPost") && x.desc.equals("(Lnet/neoforged/neoforge/client/event/ScreenEvent$Render$Post;)V"))
            .findFirst().orElseThrow();

        MethodInsnNode filter=null;
        for(AbstractInsnNode n=m.instructions.getFirst();n!=null;n=n.getNext()) {
            if(n instanceof MethodInsnNode mi && mi.getOpcode()==Opcodes.INVOKEVIRTUAL
                && mi.owner.equals("net/minecraft/client/renderer/texture/AbstractTexture")
                && mi.name.equals("setFilter") && mi.desc.equals("(ZZ)V")) {
                if(filter!=null) throw new IllegalStateException("multiple setFilter calls");
                filter=mi;
            }
        }
        if(filter==null) throw new IllegalStateException("setFilter not found");
        AbstractInsnNode mip=prevReal(filter), blur=prevReal(mip);
        m.instructions.set(blur,new InsnNode(Opcodes.ICONST_1));
        m.instructions.set(mip,new InsnNode(Opcodes.ICONST_1));

        MethodInsnNode blit=null;
        for(AbstractInsnNode n=m.instructions.getFirst();n!=null;n=n.getNext()) {
            if(n instanceof MethodInsnNode mi && mi.getOpcode()==Opcodes.INVOKEVIRTUAL
                && mi.owner.equals("net/minecraft/client/gui/GuiGraphics")
                && mi.name.equals("blit") && mi.desc.equals(BLIT)) {
                if(blit!=null) throw new IllegalStateException("multiple logo blits");
                blit=mi;
            }
        }
        if(blit==null) throw new IllegalStateException("logo blit not found");
        FieldInsnNode logoGet=null;
        for(AbstractInsnNode n=blit.getPrevious();n!=null;n=n.getPrevious()) {
            if(n instanceof FieldInsnNode fi && fi.getOpcode()==Opcodes.GETSTATIC && fi.owner.equals(OWNER) && fi.name.equals("LOGO_TEXTURE")) { logoGet=fi; break; }
        }
        if(logoGet==null) throw new IllegalStateException("logo field prelude not found");
        AbstractInsnNode start=prevReal(logoGet);
        if(!(start instanceof VarInsnNode vi) || vi.getOpcode()!=Opcodes.ALOAD || vi.var!=3) throw new IllegalStateException("GuiGraphics ALOAD 3 prelude not found");

        InsnList repl=new InsnList();
        repl.add(new VarInsnNode(Opcodes.ALOAD,3));
        repl.add(new FieldInsnNode(Opcodes.GETSTATIC,OWNER,"LOGO_TEXTURE","Lnet/minecraft/resources/ResourceLocation;"));
        repl.add(intInsn(8)); repl.add(intInsn(12));
        repl.add(intInsn(24)); repl.add(intInsn(24));
        repl.add(new InsnNode(Opcodes.FCONST_0)); repl.add(new InsnNode(Opcodes.FCONST_0));
        repl.add(intInsn(48)); repl.add(intInsn(48));
        repl.add(intInsn(48)); repl.add(intInsn(48));
        repl.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL,"net/minecraft/client/gui/GuiGraphics","blit",BLIT,false));
        m.instructions.insertBefore(start,repl);
        AbstractInsnNode end=blit.getNext();
        for(AbstractInsnNode n=start;n!=end;) { AbstractInsnNode next=n.getNext(); m.instructions.remove(n); n=next; }

        int moved=0;
        for(AbstractInsnNode n=m.instructions.getFirst();n!=null;n=n.getNext()) {
            if(n instanceof MethodInsnNode mi && mi.getOpcode()==Opcodes.INVOKEVIRTUAL
                && mi.owner.equals("net/minecraft/client/gui/GuiGraphics")
                && mi.name.equals("drawString")
                && mi.desc.equals("(Lnet/minecraft/client/gui/Font;Ljava/lang/String;IIIZ)I")) {
                AbstractInsnNode shadow=prevReal(n), color=prevReal(shadow), y=prevReal(color), x=prevReal(y);
                int xv=intValue(x);
                if(xv==47) { m.instructions.set(x,intInsn(36)); moved++; }
            }
        }
        if(moved!=3) throw new IllegalStateException("expected three text x changes, got "+moved);

        ClassWriter cw=new SafeClassWriter(ClassWriter.COMPUTE_FRAMES|ClassWriter.COMPUTE_MAXS);
        cn.accept(cw); return cw.toByteArray();
    }

    static int readInt(byte[] b,int o){ return ((b[o]&255)<<24)|((b[o+1]&255)<<16)|((b[o+2]&255)<<8)|(b[o+3]&255); }
    static AbstractInsnNode prevReal(AbstractInsnNode n){
        n=n.getPrevious();
        while(n!=null && (n.getType()==AbstractInsnNode.LABEL || n.getType()==AbstractInsnNode.LINE || n.getType()==AbstractInsnNode.FRAME)) n=n.getPrevious();
        return n;
    }
    static int intValue(AbstractInsnNode n){
        int op=n.getOpcode();
        if(op>=Opcodes.ICONST_M1 && op<=Opcodes.ICONST_5) return op-Opcodes.ICONST_0;
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
