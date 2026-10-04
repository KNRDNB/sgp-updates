import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.jar.*;
import jdk.internal.org.objectweb.asm.*;
import jdk.internal.org.objectweb.asm.tree.*;

public class BrandingFixV125 {
    private static final String OWNER = "sgp/client/branding/SgpClientBranding";
    private static final String CLASS = OWNER + ".class";
    private static final String LOGO = "assets/sgp_client_branding/textures/gui/sgp_logo.png";
    private static final String SCALED_BLIT = "(Lnet/minecraft/resources/ResourceLocation;IIIIFFIIII)V";

    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("usage: BrandingFixV125 <branding-1.2.4.jar> <logo72x24.png> <out.jar>");
        Path in=Path.of(args[0]), logo=Path.of(args[1]), out=Path.of(args[2]);
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
        if(!entries.containsKey(CLASS) || !entries.containsKey(LOGO)) throw new IllegalStateException("unexpected Branding 1.2.4 layout");
        String toml=new String(entries.get("META-INF/neoforge.mods.toml"),StandardCharsets.UTF_8);
        if(!toml.contains("version=\"1.2.4\"")) throw new IllegalStateException("expected Branding 1.2.4");
        toml=toml.replace("version=\"1.2.4\"","version=\"1.2.5\"")
            .replace("Persistent title-screen SGP badge with full transparent scaled logo, stable/test prerelease version display, blinking update notice and Installer launch button.",
                     "Persistent title-screen SGP badge with pixel-clean 1:1 transparent logo, stable/test prerelease version display, blinking update notice and Installer launch button.");
        entries.put("META-INF/neoforge.mods.toml",toml.getBytes(StandardCharsets.UTF_8));
        entries.put(CLASS,patch(entries.get(CLASS)));
        entries.put(LOGO,Files.readAllBytes(logo));

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

        // Disable linear filtering: exact 72x24 pixel-clean texture is rendered 1:1 in GUI coordinates.
        MethodInsnNode filter=null;
        for(AbstractInsnNode n=m.instructions.getFirst();n!=null;n=n.getNext()) {
            if(n instanceof MethodInsnNode mi && mi.getOpcode()==Opcodes.INVOKEVIRTUAL
                && mi.owner.equals("net/minecraft/client/renderer/texture/AbstractTexture")
                && mi.name.equals("setFilter") && mi.desc.equals("(ZZ)V")) {
                if(filter!=null) throw new IllegalStateException("multiple setFilter calls");
                filter=mi;
            }
        }
        if(filter==null) throw new IllegalStateException("setFilter call not found");
        AbstractInsnNode mip=prevReal(filter), blur=prevReal(mip);
        if(mip.getOpcode()!=Opcodes.ICONST_0 || blur.getOpcode()!=Opcodes.ICONST_1)
            throw new IllegalStateException("expected setFilter(true,false) in Branding 1.2.4");
        m.instructions.set(blur,new InsnNode(Opcodes.ICONST_0));

        MethodInsnNode blit=null;
        for(AbstractInsnNode n=m.instructions.getFirst();n!=null;n=n.getNext()) {
            if(n instanceof MethodInsnNode mi && mi.getOpcode()==Opcodes.INVOKEVIRTUAL
                && mi.owner.equals("net/minecraft/client/gui/GuiGraphics")
                && mi.name.equals("blit") && mi.desc.equals(SCALED_BLIT)) {
                if(blit!=null) throw new IllegalStateException("multiple logo blits");
                blit=mi;
            }
        }
        if(blit==null) throw new IllegalStateException("scaled logo blit not found");

        FieldInsnNode logoGet=null;
        for(AbstractInsnNode n=blit.getPrevious();n!=null;n=n.getPrevious()) {
            if(n instanceof FieldInsnNode fi && fi.getOpcode()==Opcodes.GETSTATIC
                && fi.owner.equals(OWNER) && fi.name.equals("LOGO_TEXTURE")) { logoGet=fi; break; }
        }
        if(logoGet==null) throw new IllegalStateException("logo field prelude not found");
        AbstractInsnNode start=prevReal(logoGet);
        if(!(start instanceof VarInsnNode vi) || vi.getOpcode()!=Opcodes.ALOAD || vi.var!=3)
            throw new IllegalStateException("GuiGraphics ALOAD 3 prelude not found");

        InsnList repl=new InsnList();
        repl.add(new VarInsnNode(Opcodes.ALOAD,3));
        repl.add(new FieldInsnNode(Opcodes.GETSTATIC,OWNER,"LOGO_TEXTURE","Lnet/minecraft/resources/ResourceLocation;"));
        repl.add(intInsn(8)); repl.add(intInsn(12));     // x,y
        repl.add(intInsn(72)); repl.add(intInsn(24));   // destination 72x24
        repl.add(new InsnNode(Opcodes.FCONST_0)); repl.add(new InsnNode(Opcodes.FCONST_0));
        repl.add(intInsn(72)); repl.add(intInsn(24));   // full source region 72x24
        repl.add(intInsn(72)); repl.add(intInsn(24));   // texture size 72x24
        repl.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL,
            "net/minecraft/client/gui/GuiGraphics","blit",SCALED_BLIT,false));
        m.instructions.insertBefore(start,repl);
        AbstractInsnNode end=blit.getNext();
        for(AbstractInsnNode n=start;n!=end;) { AbstractInsnNode next=n.getNext(); m.instructions.remove(n); n=next; }

        ClassWriter cw=new SafeClassWriter(ClassWriter.COMPUTE_FRAMES|ClassWriter.COMPUTE_MAXS);
        cn.accept(cw); return cw.toByteArray();
    }

    static AbstractInsnNode prevReal(AbstractInsnNode n){
        n=n.getPrevious();
        while(n!=null && (n.getType()==AbstractInsnNode.LABEL || n.getType()==AbstractInsnNode.LINE || n.getType()==AbstractInsnNode.FRAME)) n=n.getPrevious();
        return n;
    }
    static AbstractInsnNode intInsn(int v){
        if(v>=-1&&v<=5)return new InsnNode(Opcodes.ICONST_0+v);
        if(v>=Byte.MIN_VALUE&&v<=Byte.MAX_VALUE)return new IntInsnNode(Opcodes.BIPUSH,v);
        if(v>=Short.MIN_VALUE&&v<=Short.MAX_VALUE)return new IntInsnNode(Opcodes.SIPUSH,v);
        return new LdcInsnNode(v);
    }
    static final class SafeClassWriter extends ClassWriter {
        SafeClassWriter(int f){super(f);}
        @Override protected String getCommonSuperClass(String a,String b){return "java/lang/Object";}
    }
}
