<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE eagle SYSTEM "eagle.dtd">
<eagle version="9.7.0">
<drawing>
<settings>
<setting alwaysvectorfont="no"/>
<setting keepoldvectorfont="yes"/>
<setting verticaltext="up"/>
</settings>
<grid distance="0.1" unitdist="inch" unit="inch" style="lines" multiple="1" display="no" altdistance="0.01" altunitdist="inch" altunit="inch"/>
<layers>
<layer number="1" name="Top" color="4" fill="1" visible="no" active="no"/>
<layer number="2" name="Route2" color="16" fill="1" visible="no" active="no"/>
<layer number="15" name="Route15" color="23" fill="1" visible="no" active="no"/>
<layer number="16" name="Bottom" color="1" fill="1" visible="no" active="no"/>
<layer number="17" name="Pads" color="2" fill="1" visible="no" active="no"/>
<layer number="18" name="Vias" color="2" fill="1" visible="no" active="no"/>
<layer number="19" name="Unrouted" color="6" fill="1" visible="no" active="no"/>
<layer number="20" name="Dimension" color="24" fill="1" visible="no" active="no"/>
<layer number="21" name="tPlace" color="7" fill="1" visible="no" active="no"/>
<layer number="22" name="bPlace" color="7" fill="1" visible="no" active="no"/>
<layer number="23" name="tOrigins" color="15" fill="1" visible="no" active="no"/>
<layer number="24" name="bOrigins" color="15" fill="1" visible="no" active="no"/>
<layer number="25" name="tNames" color="7" fill="1" visible="no" active="no"/>
<layer number="26" name="bNames" color="7" fill="1" visible="no" active="no"/>
<layer number="27" name="tValues" color="7" fill="1" visible="no" active="no"/>
<layer number="28" name="bValues" color="7" fill="1" visible="no" active="no"/>
<layer number="29" name="tStop" color="7" fill="3" visible="no" active="no"/>
<layer number="30" name="bStop" color="7" fill="6" visible="no" active="no"/>
<layer number="31" name="tCream" color="7" fill="4" visible="no" active="no"/>
<layer number="32" name="bCream" color="7" fill="5" visible="no" active="no"/>
<layer number="33" name="tFinish" color="6" fill="3" visible="no" active="no"/>
<layer number="34" name="bFinish" color="6" fill="6" visible="no" active="no"/>
<layer number="35" name="tGlue" color="7" fill="4" visible="no" active="no"/>
<layer number="36" name="bGlue" color="7" fill="5" visible="no" active="no"/>
<layer number="37" name="tTest" color="7" fill="1" visible="no" active="no"/>
<layer number="38" name="bTest" color="7" fill="1" visible="no" active="no"/>
<layer number="39" name="tKeepout" color="4" fill="11" visible="no" active="no"/>
<layer number="40" name="bKeepout" color="1" fill="11" visible="no" active="no"/>
<layer number="41" name="tRestrict" color="4" fill="8" visible="no" active="no"/>
<layer number="42" name="bRestrict" color="1" fill="10" visible="no" active="no"/>
<layer number="43" name="vRestrict" color="2" fill="10" visible="no" active="no"/>
<layer number="44" name="Drills" color="7" fill="1" visible="no" active="no"/>
<layer number="45" name="Holes" color="7" fill="1" visible="no" active="no"/>
<layer number="46" name="Milling" color="3" fill="1" visible="no" active="no"/>
<layer number="47" name="Measures" color="7" fill="1" visible="no" active="no"/>
<layer number="48" name="Document" color="7" fill="1" visible="no" active="no"/>
<layer number="49" name="Reference" color="7" fill="1" visible="no" active="no"/>
<layer number="50" name="dxf" color="7" fill="1" visible="no" active="no"/>
<layer number="51" name="tDocu" color="7" fill="1" visible="no" active="no"/>
<layer number="52" name="bDocu" color="7" fill="1" visible="no" active="no"/>
<layer number="88" name="SimResults" color="9" fill="1" visible="yes" active="yes"/>
<layer number="89" name="SimProbes" color="9" fill="1" visible="yes" active="yes"/>
<layer number="91" name="Nets" color="2" fill="1" visible="yes" active="yes"/>
<layer number="92" name="Busses" color="1" fill="1" visible="yes" active="yes"/>
<layer number="93" name="Pins" color="2" fill="1" visible="no" active="yes"/>
<layer number="94" name="Symbols" color="4" fill="1" visible="yes" active="yes"/>
<layer number="95" name="Names" color="7" fill="1" visible="yes" active="yes"/>
<layer number="96" name="Values" color="7" fill="1" visible="yes" active="yes"/>
<layer number="97" name="Info" color="7" fill="1" visible="yes" active="yes"/>
<layer number="98" name="Guide" color="6" fill="1" visible="yes" active="yes"/>
<layer number="250" name="Descript" color="7" fill="1" visible="no" active="no"/>
<layer number="251" name="SMDround" color="7" fill="11" visible="no" active="no"/>
</layers>
<schematic xreflabel="%F%N/%S.%C%R" xrefpart="/%S.%C%R">
<libraries>
<library name="k1">
<packages>
<package name="C36A">
<pad name="1" x="-44.45" y="0" drill="1.016" shape="octagon"/>
<pad name="2" x="-41.91" y="0" drill="1.016" shape="octagon"/>
<pad name="3" x="-39.37" y="0" drill="1.016" shape="octagon"/>
<pad name="4" x="-36.83" y="0" drill="1.016" shape="octagon"/>
<pad name="5" x="-34.29" y="0" drill="1.016" shape="octagon"/>
<pad name="6" x="-31.75" y="0" drill="1.016" shape="octagon"/>
<pad name="7" x="-29.21" y="0" drill="1.016" shape="octagon"/>
<pad name="8" x="-26.67" y="0" drill="1.016" shape="octagon"/>
<pad name="9" x="-24.13" y="0" drill="1.016" shape="octagon"/>
<pad name="10" x="-21.59" y="0" drill="1.016" shape="octagon"/>
<pad name="11" x="-19.05" y="0" drill="1.016" shape="octagon"/>
<pad name="12" x="-16.51" y="0" drill="1.016" shape="octagon"/>
<pad name="13" x="-13.97" y="0" drill="1.016" shape="octagon"/>
<pad name="14" x="-11.43" y="0" drill="1.016" shape="octagon"/>
<pad name="15" x="-8.89" y="0" drill="1.016" shape="octagon"/>
<pad name="16" x="-6.35" y="0" drill="1.016" shape="octagon"/>
<pad name="17" x="-3.81" y="0" drill="1.016" shape="octagon"/>
<pad name="18" x="-1.27" y="0" drill="1.016" shape="octagon"/>
<pad name="19" x="1.27" y="0" drill="1.016" shape="octagon"/>
<pad name="20" x="3.81" y="0" drill="1.016" shape="octagon"/>
<pad name="21" x="6.35" y="0" drill="1.016" shape="octagon"/>
<pad name="22" x="8.89" y="0" drill="1.016" shape="octagon"/>
<pad name="23" x="11.43" y="0" drill="1.016" shape="octagon"/>
<pad name="24" x="13.97" y="0" drill="1.016" shape="octagon"/>
<pad name="25" x="16.51" y="0" drill="1.016" shape="octagon"/>
<pad name="26" x="19.05" y="0" drill="1.016" shape="octagon"/>
<pad name="27" x="21.59" y="0" drill="1.016" shape="octagon"/>
<pad name="28" x="24.13" y="0" drill="1.016" shape="octagon"/>
<pad name="29" x="26.67" y="0" drill="1.016" shape="octagon"/>
<pad name="30" x="29.21" y="0" drill="1.016" shape="octagon"/>
<pad name="31" x="-46.99" y="0" drill="1.016" shape="octagon"/>
<pad name="32" x="-49.53" y="0" drill="1.016" shape="octagon"/>
<pad name="33" x="-52.07" y="0" drill="1.016" shape="octagon"/>
<pad name="34" x="31.75" y="0" drill="1.016" shape="octagon"/>
<pad name="35" x="34.29" y="0" drill="1.016" shape="octagon"/>
<pad name="36" x="36.83" y="0" drill="1.016" shape="octagon"/>
<text x="-43.815" y="1.27" size="1.016" layer="21" rot="SR90">VCC</text>
<text x="-41.275" y="1.27" size="1.016" layer="21" rot="SR90">D0</text>
<text x="-38.735" y="1.27" size="1.016" layer="21" rot="SR90">D1</text>
<text x="-36.195" y="1.27" size="1.016" layer="21" rot="SR90">D2</text>
<text x="-33.655" y="1.27" size="1.016" layer="21" rot="SR90">D3</text>
<text x="-31.115" y="1.27" size="1.016" layer="21" rot="SR90">D4</text>
<text x="-28.575" y="1.27" size="1.016" layer="21" rot="SR90">D5</text>
<text x="-26.035" y="1.27" size="1.016" layer="21" rot="SR90">D6</text>
<text x="-23.495" y="1.27" size="1.016" layer="21" rot="SR90">D7</text>
<text x="-20.955" y="1.27" size="1.27" layer="21" rot="SR90">Q</text>
<text x="-18.415" y="1.27" size="1.016" layer="21" rot="SR90">TPA</text>
<text x="-15.875" y="1.27" size="1.016" layer="21" rot="SR90">TPB</text>
<text x="-8.255" y="1.27" size="1.016" layer="21" rot="SR90">A0</text>
<text x="-5.715" y="1.27" size="1.016" layer="21" rot="SR90">A1</text>
<text x="-3.175" y="1.27" size="1.016" layer="21" rot="SR90">A2</text>
<text x="-0.635" y="1.27" size="1.016" layer="21" rot="SR90">A3</text>
<text x="1.905" y="1.27" size="1.016" layer="21" rot="SR90">A4</text>
<text x="4.445" y="1.27" size="1.016" layer="21" rot="SR90">A5</text>
<text x="6.985" y="1.27" size="1.016" layer="21" rot="SR90">A6</text>
<text x="9.525" y="1.27" size="1.016" layer="21" rot="SR90">A7</text>
<text x="12.065" y="1.27" size="1.016" layer="21" rot="SR90">-INT</text>
<text x="14.605" y="1.27" size="1.016" layer="21" rot="SR90">N2</text>
<text x="17.145" y="1.27" size="1.016" layer="21" rot="SR90">-EF</text>
<text x="24.765" y="1.27" size="1.016" layer="21" rot="SR90">N1</text>
<text x="27.305" y="1.27" size="1.016" layer="21" rot="SR90">N0</text>
<text x="29.845" y="1.27" size="1.016" layer="21" rot="SR90">GND</text>
<text x="19.685" y="1.27" size="1.016" layer="21" rot="SR90">-VMA</text>
<text x="22.225" y="1.27" size="1.016" layer="21" rot="SR90">-RES</text>
<text x="-10.795" y="1.27" size="1.016" layer="21" rot="SR90">-MRW</text>
<text x="-13.335" y="1.27" size="1.016" layer="21" rot="SR90">-MRD</text>
<text x="-51.435" y="1.27" size="1.016" layer="21" rot="SR90">-EF1</text>
<text x="-48.895" y="1.27" size="1.016" layer="21" rot="SR90">-EF2</text>
<text x="-46.355" y="1.27" size="1.016" layer="21" rot="SR90">-EF3</text>
<text x="32.385" y="1.27" size="1.016" layer="21" rot="SR90">-INP</text>
<text x="34.925" y="1.27" size="1.016" layer="21" rot="SR90">-OUT</text>
<text x="37.465" y="1.27" size="1.016" layer="21" rot="SR90">EXP</text>
</package>
</packages>
<symbols>
<symbol name="C36">
<wire x1="-52.07" y1="-6.35" x2="-52.07" y2="6.35" width="0.254" layer="94"/>
<wire x1="-52.07" y1="6.35" x2="39.37" y2="6.35" width="0.254" layer="94"/>
<wire x1="39.37" y1="6.35" x2="39.37" y2="-6.35" width="0.254" layer="94"/>
<wire x1="39.37" y1="-6.35" x2="-52.07" y2="-6.35" width="0.254" layer="94"/>
<pin name="+5V" x="-43.18" y="10.16" length="middle" direction="pwr" rot="R270"/>
<pin name="D0" x="-40.64" y="10.16" length="middle" rot="R270"/>
<pin name="D1" x="-38.1" y="10.16" length="middle" rot="R270"/>
<pin name="D2" x="-35.56" y="10.16" length="middle" rot="R270"/>
<pin name="D3" x="-33.02" y="10.16" length="middle" rot="R270"/>
<pin name="D4" x="-30.48" y="10.16" length="middle" rot="R270"/>
<pin name="D5" x="-27.94" y="10.16" length="middle" rot="R270"/>
<pin name="D6" x="-25.4" y="10.16" length="middle" rot="R270"/>
<pin name="D7" x="-22.86" y="10.16" length="middle" rot="R270"/>
<pin name="Q" x="-20.32" y="10.16" length="middle" rot="R270"/>
<pin name="TPA" x="-17.78" y="10.16" length="middle" rot="R270"/>
<pin name="TPB" x="-15.24" y="10.16" length="middle" rot="R270"/>
<pin name="-MRD" x="-12.7" y="10.16" length="middle" rot="R270"/>
<pin name="-MRW" x="-10.16" y="10.16" length="middle" rot="R270"/>
<pin name="A0" x="-7.62" y="10.16" length="middle" rot="R270"/>
<pin name="A1" x="-5.08" y="10.16" length="middle" rot="R270"/>
<pin name="A2" x="-2.54" y="10.16" length="middle" rot="R270"/>
<pin name="A3" x="0" y="10.16" length="middle" rot="R270"/>
<pin name="A4" x="2.54" y="10.16" length="middle" rot="R270"/>
<pin name="A5" x="5.08" y="10.16" length="middle" rot="R270"/>
<pin name="A6" x="7.62" y="10.16" length="middle" rot="R270"/>
<pin name="A7" x="10.16" y="10.16" length="middle" rot="R270"/>
<pin name="-INT" x="12.7" y="10.16" length="middle" rot="R270"/>
<pin name="N2" x="15.24" y="10.16" length="middle" rot="R270"/>
<pin name="-EF" x="17.78" y="10.16" length="middle" rot="R270"/>
<pin name="-VMA" x="20.32" y="10.16" length="middle" rot="R270"/>
<pin name="-RESET" x="22.86" y="10.16" length="middle" rot="R270"/>
<pin name="N1" x="25.4" y="10.16" length="middle" rot="R270"/>
<pin name="N0" x="27.94" y="10.16" length="middle" rot="R270"/>
<pin name="GND" x="30.48" y="10.16" length="middle" direction="sup" rot="R270"/>
<pin name="-EF1" x="-50.8" y="10.16" length="middle" rot="R270"/>
<pin name="-EF2" x="-48.26" y="10.16" length="middle" rot="R270"/>
<pin name="-EF3" x="-45.72" y="10.16" length="middle" rot="R270"/>
<pin name="-INP" x="33.02" y="10.16" length="middle" rot="R270"/>
<pin name="-OUT" x="35.56" y="10.16" length="middle" rot="R270"/>
<pin name="EXP" x="38.1" y="10.16" length="middle" rot="R270"/>
</symbol>
</symbols>
<devicesets>
<deviceset name="C36A">
<gates>
<gate name="G$1" symbol="C36" x="-2.54" y="0"/>
</gates>
<devices>
<device name="" package="C36A">
<connects>
<connect gate="G$1" pin="+5V" pad="1"/>
<connect gate="G$1" pin="-EF" pad="25"/>
<connect gate="G$1" pin="-EF1" pad="31"/>
<connect gate="G$1" pin="-EF2" pad="32"/>
<connect gate="G$1" pin="-EF3" pad="33"/>
<connect gate="G$1" pin="-INP" pad="34"/>
<connect gate="G$1" pin="-INT" pad="23"/>
<connect gate="G$1" pin="-MRD" pad="13"/>
<connect gate="G$1" pin="-MRW" pad="14"/>
<connect gate="G$1" pin="-OUT" pad="35"/>
<connect gate="G$1" pin="-RESET" pad="27"/>
<connect gate="G$1" pin="-VMA" pad="26"/>
<connect gate="G$1" pin="A0" pad="15"/>
<connect gate="G$1" pin="A1" pad="16"/>
<connect gate="G$1" pin="A2" pad="17"/>
<connect gate="G$1" pin="A3" pad="18"/>
<connect gate="G$1" pin="A4" pad="19"/>
<connect gate="G$1" pin="A5" pad="20"/>
<connect gate="G$1" pin="A6" pad="21"/>
<connect gate="G$1" pin="A7" pad="22"/>
<connect gate="G$1" pin="D0" pad="2"/>
<connect gate="G$1" pin="D1" pad="3"/>
<connect gate="G$1" pin="D2" pad="4"/>
<connect gate="G$1" pin="D3" pad="5"/>
<connect gate="G$1" pin="D4" pad="6"/>
<connect gate="G$1" pin="D5" pad="7"/>
<connect gate="G$1" pin="D6" pad="8"/>
<connect gate="G$1" pin="D7" pad="9"/>
<connect gate="G$1" pin="EXP" pad="36"/>
<connect gate="G$1" pin="GND" pad="30"/>
<connect gate="G$1" pin="N0" pad="29"/>
<connect gate="G$1" pin="N1" pad="28"/>
<connect gate="G$1" pin="N2" pad="24"/>
<connect gate="G$1" pin="Q" pad="10"/>
<connect gate="G$1" pin="TPA" pad="11"/>
<connect gate="G$1" pin="TPB" pad="12"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
</devices>
</deviceset>
</devicesets>
</library>
<library name="con-phoenix-254">
<packages>
<package name="2POL254">
<description>&lt;b&gt;PHOENIX CONNECTOR&lt;/b&gt;</description>
<wire x1="-2.67" y1="-1.45" x2="2.67" y2="-1.45" width="0.254" layer="21"/>
<wire x1="2.67" y1="-1.45" x2="2.67" y2="1.45" width="0.254" layer="21"/>
<wire x1="2.67" y1="1.45" x2="-2.67" y2="1.45" width="0.254" layer="21"/>
<wire x1="-2.67" y1="1.45" x2="-2.67" y2="-1.45" width="0.254" layer="21"/>
<wire x1="-2.56" y1="1.1" x2="2.56" y2="1.1" width="0.1524" layer="21"/>
<wire x1="-1.905" y1="-0.508" x2="-0.762" y2="0.635" width="0.1524" layer="51"/>
<wire x1="0.508" y1="-0.254" x2="2.032" y2="0.127" width="0.1524" layer="51"/>
<circle x="-1.27" y="0" radius="0.889" width="0.1524" layer="51"/>
<circle x="1.27" y="0" radius="0.889" width="0.1524" layer="51"/>
<pad name="1" x="-1.27" y="0" drill="1.2" shape="long" rot="R90"/>
<pad name="2" x="1.27" y="0" drill="1.2" shape="long" rot="R90"/>
<text x="-2.794" y="1.778" size="1.27" layer="25">&gt;NAME</text>
<text x="-2.794" y="-3.048" size="1.27" layer="27">&gt;VALUE</text>
</package>
</packages>
<symbols>
<symbol name="SKB">
<wire x1="2.032" y1="0.762" x2="0.508" y2="-0.762" width="0.254" layer="94"/>
<circle x="1.27" y="0" radius="1.27" width="0.254" layer="94"/>
<text x="3.556" y="-0.635" size="1.778" layer="95">&gt;NAME</text>
<pin name="1" x="-2.54" y="0" visible="pad" length="short" direction="pas"/>
</symbol>
<symbol name="SKBV">
<wire x1="2.032" y1="0.762" x2="0.508" y2="-0.762" width="0.254" layer="94"/>
<circle x="1.27" y="0" radius="1.27" width="0.254" layer="94"/>
<text x="3.556" y="-0.635" size="1.778" layer="95">&gt;NAME</text>
<text x="-1.016" y="-3.302" size="1.778" layer="96">&gt;VALUE</text>
<pin name="1" x="-2.54" y="0" visible="pad" length="short" direction="pas"/>
</symbol>
</symbols>
<devicesets>
<deviceset name="MPT2" prefix="X" uservalue="yes">
<description>&lt;b&gt;PHOENIX CONNECTOR&lt;/b&gt;</description>
<gates>
<gate name="-1" symbol="SKB" x="0" y="0" addlevel="always"/>
<gate name="-2" symbol="SKBV" x="0" y="-5.08" addlevel="always"/>
</gates>
<devices>
<device name="" package="2POL254">
<connects>
<connect gate="-1" pin="1" pad="1"/>
<connect gate="-2" pin="1" pad="2"/>
</connects>
<technologies>
<technology name=""/>
</technologies>
</device>
</devices>
</deviceset>
</devicesets>
</library>
</libraries>
<attributes>
</attributes>
<variantdefs>
</variantdefs>
<classes>
<class number="0" name="default" width="0" drill="0">
</class>
</classes>
<parts>
<part name="U$1" library="k1" deviceset="C36A" device=""/>
<part name="U$2" library="k1" deviceset="C36A" device=""/>
<part name="U$3" library="k1" deviceset="C36A" device=""/>
<part name="U$4" library="k1" deviceset="C36A" device=""/>
<part name="U$5" library="k1" deviceset="C36A" device=""/>
<part name="U$6" library="k1" deviceset="C36A" device=""/>
<part name="X1" library="con-phoenix-254" deviceset="MPT2" device=""/>
</parts>
<sheets>
<sheet>
<plain>
</plain>
<instances>
<instance part="U$1" gate="G$1" x="-53.34" y="43.18" smashed="yes" rot="R270"/>
<instance part="U$2" gate="G$1" x="22.86" y="43.18" smashed="yes" rot="R270"/>
<instance part="U$3" gate="G$1" x="-15.24" y="43.18" smashed="yes" rot="R270"/>
<instance part="U$4" gate="G$1" x="60.96" y="43.18" smashed="yes" rot="R270"/>
<instance part="U$5" gate="G$1" x="99.06" y="43.18" smashed="yes" rot="R270"/>
<instance part="U$6" gate="G$1" x="137.16" y="43.18" smashed="yes" rot="R270"/>
<instance part="X1" gate="-1" x="-10.16" y="114.3" smashed="yes">
<attribute name="NAME" x="-6.604" y="113.665" size="1.778" layer="95"/>
</instance>
<instance part="X1" gate="-2" x="-10.16" y="119.38" smashed="yes">
<attribute name="NAME" x="-6.604" y="118.745" size="1.778" layer="95"/>
<attribute name="VALUE" x="-11.176" y="116.078" size="1.778" layer="96"/>
</instance>
</instances>
<busses>
<bus name="5V,GND,D[0..7],Q,TPA,TPB,MRD,MRW,A[0..7],INT,EF,VMA,RESET,N0,N1,N2,EF1,EF2,EF3,INP,OUT,IOM">
<segment>
<wire x1="-25.4" y1="93.98" x2="-25.4" y2="5.08" width="0.762" layer="92"/>
</segment>
<segment>
<wire x1="50.8" y1="93.98" x2="50.8" y2="5.08" width="0.762" layer="92"/>
</segment>
<segment>
<wire x1="12.7" y1="93.98" x2="12.7" y2="5.08" width="0.762" layer="92"/>
</segment>
<segment>
<wire x1="88.9" y1="93.98" x2="88.9" y2="5.08" width="0.762" layer="92"/>
</segment>
<segment>
<wire x1="127" y1="93.98" x2="127" y2="5.08" width="0.762" layer="92"/>
</segment>
<segment>
<wire x1="165.1" y1="93.98" x2="165.1" y2="5.08" width="0.762" layer="92"/>
</segment>
</bus>
</busses>
<nets>
<net name="5V" class="0">
<segment>
<wire x1="50.8" y1="86.36" x2="33.02" y2="86.36" width="0.1524" layer="91"/>
<label x="38.1" y="86.36" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="+5V"/>
</segment>
<segment>
<wire x1="88.9" y1="86.36" x2="71.12" y2="86.36" width="0.1524" layer="91"/>
<label x="76.2" y="86.36" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="+5V"/>
</segment>
<segment>
<wire x1="12.7" y1="86.36" x2="-5.08" y2="86.36" width="0.1524" layer="91"/>
<label x="0" y="86.36" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="+5V"/>
</segment>
<segment>
<wire x1="127" y1="86.36" x2="109.22" y2="86.36" width="0.1524" layer="91"/>
<label x="119.38" y="86.36" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="+5V"/>
</segment>
<segment>
<wire x1="-25.4" y1="86.36" x2="-43.18" y2="86.36" width="0.1524" layer="91"/>
<label x="-33.02" y="86.36" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="+5V"/>
</segment>
<segment>
<wire x1="165.1" y1="86.36" x2="147.32" y2="86.36" width="0.1524" layer="91"/>
<label x="152.4" y="86.36" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="+5V"/>
</segment>
</net>
<net name="D0" class="0">
<segment>
<wire x1="-25.4" y1="83.82" x2="-43.18" y2="83.82" width="0.1524" layer="91"/>
<label x="-38.1" y="83.82" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="D0"/>
</segment>
<segment>
<wire x1="50.8" y1="83.82" x2="33.02" y2="83.82" width="0.1524" layer="91"/>
<label x="38.1" y="83.82" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="D0"/>
</segment>
<segment>
<wire x1="12.7" y1="83.82" x2="-5.08" y2="83.82" width="0.1524" layer="91"/>
<label x="0" y="83.82" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="D0"/>
</segment>
<segment>
<wire x1="88.9" y1="83.82" x2="71.12" y2="83.82" width="0.1524" layer="91"/>
<label x="76.2" y="83.82" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="D0"/>
</segment>
<segment>
<wire x1="127" y1="83.82" x2="109.22" y2="83.82" width="0.1524" layer="91"/>
<label x="114.3" y="83.82" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="D0"/>
</segment>
<segment>
<wire x1="165.1" y1="83.82" x2="147.32" y2="83.82" width="0.1524" layer="91"/>
<label x="152.4" y="83.82" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="D0"/>
</segment>
</net>
<net name="D1" class="0">
<segment>
<wire x1="-25.4" y1="81.28" x2="-43.18" y2="81.28" width="0.1524" layer="91"/>
<label x="-38.1" y="81.28" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="D1"/>
</segment>
<segment>
<wire x1="50.8" y1="81.28" x2="33.02" y2="81.28" width="0.1524" layer="91"/>
<label x="38.1" y="81.28" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="D1"/>
</segment>
<segment>
<wire x1="12.7" y1="81.28" x2="-5.08" y2="81.28" width="0.1524" layer="91"/>
<label x="0" y="81.28" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="D1"/>
</segment>
<segment>
<wire x1="88.9" y1="81.28" x2="71.12" y2="81.28" width="0.1524" layer="91"/>
<label x="76.2" y="81.28" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="D1"/>
</segment>
<segment>
<wire x1="127" y1="81.28" x2="109.22" y2="81.28" width="0.1524" layer="91"/>
<label x="114.3" y="81.28" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="D1"/>
</segment>
<segment>
<wire x1="165.1" y1="81.28" x2="147.32" y2="81.28" width="0.1524" layer="91"/>
<label x="152.4" y="81.28" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="D1"/>
</segment>
</net>
<net name="D2" class="0">
<segment>
<wire x1="-25.4" y1="78.74" x2="-43.18" y2="78.74" width="0.1524" layer="91"/>
<label x="-38.1" y="78.74" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="D2"/>
</segment>
<segment>
<wire x1="50.8" y1="78.74" x2="33.02" y2="78.74" width="0.1524" layer="91"/>
<label x="38.1" y="78.74" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="D2"/>
</segment>
<segment>
<wire x1="12.7" y1="78.74" x2="-5.08" y2="78.74" width="0.1524" layer="91"/>
<label x="0" y="78.74" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="D2"/>
</segment>
<segment>
<wire x1="88.9" y1="78.74" x2="71.12" y2="78.74" width="0.1524" layer="91"/>
<label x="76.2" y="78.74" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="D2"/>
</segment>
<segment>
<wire x1="127" y1="78.74" x2="109.22" y2="78.74" width="0.1524" layer="91"/>
<label x="114.3" y="78.74" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="D2"/>
</segment>
<segment>
<wire x1="165.1" y1="78.74" x2="147.32" y2="78.74" width="0.1524" layer="91"/>
<label x="152.4" y="78.74" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="D2"/>
</segment>
</net>
<net name="D3" class="0">
<segment>
<wire x1="-25.4" y1="76.2" x2="-43.18" y2="76.2" width="0.1524" layer="91"/>
<label x="-38.1" y="76.2" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="D3"/>
</segment>
<segment>
<wire x1="50.8" y1="76.2" x2="33.02" y2="76.2" width="0.1524" layer="91"/>
<label x="38.1" y="76.2" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="D3"/>
</segment>
<segment>
<wire x1="12.7" y1="76.2" x2="-5.08" y2="76.2" width="0.1524" layer="91"/>
<label x="0" y="76.2" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="D3"/>
</segment>
<segment>
<wire x1="88.9" y1="76.2" x2="71.12" y2="76.2" width="0.1524" layer="91"/>
<label x="76.2" y="76.2" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="D3"/>
</segment>
<segment>
<wire x1="127" y1="76.2" x2="109.22" y2="76.2" width="0.1524" layer="91"/>
<label x="114.3" y="76.2" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="D3"/>
</segment>
<segment>
<wire x1="165.1" y1="76.2" x2="147.32" y2="76.2" width="0.1524" layer="91"/>
<label x="152.4" y="76.2" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="D3"/>
</segment>
</net>
<net name="D4" class="0">
<segment>
<wire x1="-25.4" y1="73.66" x2="-43.18" y2="73.66" width="0.1524" layer="91"/>
<label x="-38.1" y="73.66" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="D4"/>
</segment>
<segment>
<wire x1="50.8" y1="73.66" x2="33.02" y2="73.66" width="0.1524" layer="91"/>
<label x="38.1" y="73.66" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="D4"/>
</segment>
<segment>
<wire x1="12.7" y1="73.66" x2="-5.08" y2="73.66" width="0.1524" layer="91"/>
<label x="0" y="73.66" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="D4"/>
</segment>
<segment>
<wire x1="88.9" y1="73.66" x2="71.12" y2="73.66" width="0.1524" layer="91"/>
<label x="76.2" y="73.66" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="D4"/>
</segment>
<segment>
<wire x1="127" y1="73.66" x2="109.22" y2="73.66" width="0.1524" layer="91"/>
<label x="114.3" y="73.66" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="D4"/>
</segment>
<segment>
<wire x1="165.1" y1="73.66" x2="147.32" y2="73.66" width="0.1524" layer="91"/>
<label x="152.4" y="73.66" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="D4"/>
</segment>
</net>
<net name="D5" class="0">
<segment>
<wire x1="-25.4" y1="71.12" x2="-43.18" y2="71.12" width="0.1524" layer="91"/>
<label x="-38.1" y="71.12" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="D5"/>
</segment>
<segment>
<wire x1="50.8" y1="71.12" x2="33.02" y2="71.12" width="0.1524" layer="91"/>
<label x="38.1" y="71.12" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="D5"/>
</segment>
<segment>
<wire x1="12.7" y1="71.12" x2="-5.08" y2="71.12" width="0.1524" layer="91"/>
<label x="0" y="71.12" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="D5"/>
</segment>
<segment>
<wire x1="88.9" y1="71.12" x2="71.12" y2="71.12" width="0.1524" layer="91"/>
<label x="76.2" y="71.12" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="D5"/>
</segment>
<segment>
<wire x1="127" y1="71.12" x2="109.22" y2="71.12" width="0.1524" layer="91"/>
<label x="114.3" y="71.12" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="D5"/>
</segment>
<segment>
<wire x1="165.1" y1="71.12" x2="147.32" y2="71.12" width="0.1524" layer="91"/>
<label x="152.4" y="71.12" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="D5"/>
</segment>
</net>
<net name="D6" class="0">
<segment>
<wire x1="-25.4" y1="68.58" x2="-43.18" y2="68.58" width="0.1524" layer="91"/>
<label x="-38.1" y="68.58" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="D6"/>
</segment>
<segment>
<wire x1="50.8" y1="68.58" x2="33.02" y2="68.58" width="0.1524" layer="91"/>
<label x="38.1" y="68.58" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="D6"/>
</segment>
<segment>
<wire x1="12.7" y1="68.58" x2="-5.08" y2="68.58" width="0.1524" layer="91"/>
<label x="0" y="68.58" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="D6"/>
</segment>
<segment>
<wire x1="88.9" y1="68.58" x2="71.12" y2="68.58" width="0.1524" layer="91"/>
<label x="76.2" y="68.58" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="D6"/>
</segment>
<segment>
<wire x1="127" y1="68.58" x2="109.22" y2="68.58" width="0.1524" layer="91"/>
<label x="114.3" y="68.58" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="D6"/>
</segment>
<segment>
<wire x1="165.1" y1="68.58" x2="147.32" y2="68.58" width="0.1524" layer="91"/>
<label x="152.4" y="68.58" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="D6"/>
</segment>
</net>
<net name="D7" class="0">
<segment>
<wire x1="-25.4" y1="66.04" x2="-43.18" y2="66.04" width="0.1524" layer="91"/>
<label x="-38.1" y="66.04" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="D7"/>
</segment>
<segment>
<wire x1="50.8" y1="66.04" x2="33.02" y2="66.04" width="0.1524" layer="91"/>
<label x="38.1" y="66.04" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="D7"/>
</segment>
<segment>
<wire x1="12.7" y1="66.04" x2="-5.08" y2="66.04" width="0.1524" layer="91"/>
<label x="0" y="66.04" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="D7"/>
</segment>
<segment>
<wire x1="88.9" y1="66.04" x2="71.12" y2="66.04" width="0.1524" layer="91"/>
<label x="76.2" y="66.04" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="D7"/>
</segment>
<segment>
<wire x1="127" y1="66.04" x2="109.22" y2="66.04" width="0.1524" layer="91"/>
<label x="114.3" y="66.04" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="D7"/>
</segment>
<segment>
<wire x1="165.1" y1="66.04" x2="147.32" y2="66.04" width="0.1524" layer="91"/>
<label x="152.4" y="66.04" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="D7"/>
</segment>
</net>
<net name="Q" class="0">
<segment>
<wire x1="-25.4" y1="63.5" x2="-43.18" y2="63.5" width="0.1524" layer="91"/>
<label x="-38.1" y="63.5" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="Q"/>
</segment>
<segment>
<wire x1="50.8" y1="63.5" x2="33.02" y2="63.5" width="0.1524" layer="91"/>
<label x="38.1" y="63.5" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="Q"/>
</segment>
<segment>
<wire x1="12.7" y1="63.5" x2="-5.08" y2="63.5" width="0.1524" layer="91"/>
<label x="0" y="63.5" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="Q"/>
</segment>
<segment>
<wire x1="88.9" y1="63.5" x2="71.12" y2="63.5" width="0.1524" layer="91"/>
<label x="76.2" y="63.5" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="Q"/>
</segment>
<segment>
<wire x1="127" y1="63.5" x2="109.22" y2="63.5" width="0.1524" layer="91"/>
<label x="114.3" y="63.5" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="Q"/>
</segment>
<segment>
<wire x1="165.1" y1="63.5" x2="147.32" y2="63.5" width="0.1524" layer="91"/>
<label x="152.4" y="63.5" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="Q"/>
</segment>
</net>
<net name="TPA" class="0">
<segment>
<wire x1="-25.4" y1="60.96" x2="-43.18" y2="60.96" width="0.1524" layer="91"/>
<label x="-38.1" y="60.96" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="TPA"/>
</segment>
<segment>
<wire x1="50.8" y1="60.96" x2="33.02" y2="60.96" width="0.1524" layer="91"/>
<label x="38.1" y="60.96" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="TPA"/>
</segment>
<segment>
<wire x1="12.7" y1="60.96" x2="-5.08" y2="60.96" width="0.1524" layer="91"/>
<label x="0" y="60.96" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="TPA"/>
</segment>
<segment>
<wire x1="88.9" y1="60.96" x2="71.12" y2="60.96" width="0.1524" layer="91"/>
<label x="76.2" y="60.96" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="TPA"/>
</segment>
<segment>
<wire x1="127" y1="60.96" x2="109.22" y2="60.96" width="0.1524" layer="91"/>
<label x="114.3" y="60.96" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="TPA"/>
</segment>
<segment>
<wire x1="165.1" y1="60.96" x2="147.32" y2="60.96" width="0.1524" layer="91"/>
<label x="152.4" y="60.96" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="TPA"/>
</segment>
</net>
<net name="TPB" class="0">
<segment>
<wire x1="-25.4" y1="58.42" x2="-43.18" y2="58.42" width="0.1524" layer="91"/>
<label x="-38.1" y="58.42" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="TPB"/>
</segment>
<segment>
<wire x1="50.8" y1="58.42" x2="33.02" y2="58.42" width="0.1524" layer="91"/>
<label x="38.1" y="58.42" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="TPB"/>
</segment>
<segment>
<wire x1="12.7" y1="58.42" x2="-5.08" y2="58.42" width="0.1524" layer="91"/>
<label x="0" y="58.42" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="TPB"/>
</segment>
<segment>
<wire x1="88.9" y1="58.42" x2="71.12" y2="58.42" width="0.1524" layer="91"/>
<label x="76.2" y="58.42" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="TPB"/>
</segment>
<segment>
<wire x1="127" y1="58.42" x2="109.22" y2="58.42" width="0.1524" layer="91"/>
<label x="114.3" y="58.42" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="TPB"/>
</segment>
<segment>
<wire x1="165.1" y1="58.42" x2="147.32" y2="58.42" width="0.1524" layer="91"/>
<label x="152.4" y="58.42" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="TPB"/>
</segment>
</net>
<net name="MRD" class="0">
<segment>
<wire x1="-25.4" y1="55.88" x2="-43.18" y2="55.88" width="0.1524" layer="91"/>
<label x="-38.1" y="55.88" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="-MRD"/>
</segment>
<segment>
<wire x1="50.8" y1="55.88" x2="33.02" y2="55.88" width="0.1524" layer="91"/>
<label x="38.1" y="55.88" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="-MRD"/>
</segment>
<segment>
<wire x1="12.7" y1="55.88" x2="-5.08" y2="55.88" width="0.1524" layer="91"/>
<label x="0" y="55.88" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="-MRD"/>
</segment>
<segment>
<wire x1="88.9" y1="55.88" x2="71.12" y2="55.88" width="0.1524" layer="91"/>
<label x="76.2" y="55.88" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="-MRD"/>
</segment>
<segment>
<wire x1="127" y1="55.88" x2="109.22" y2="55.88" width="0.1524" layer="91"/>
<label x="114.3" y="55.88" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="-MRD"/>
</segment>
<segment>
<wire x1="165.1" y1="55.88" x2="147.32" y2="55.88" width="0.1524" layer="91"/>
<label x="152.4" y="55.88" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="-MRD"/>
</segment>
</net>
<net name="MRW" class="0">
<segment>
<wire x1="-25.4" y1="53.34" x2="-43.18" y2="53.34" width="0.1524" layer="91"/>
<label x="-38.1" y="53.34" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="-MRW"/>
</segment>
<segment>
<wire x1="50.8" y1="53.34" x2="33.02" y2="53.34" width="0.1524" layer="91"/>
<label x="38.1" y="53.34" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="-MRW"/>
</segment>
<segment>
<wire x1="12.7" y1="53.34" x2="-5.08" y2="53.34" width="0.1524" layer="91"/>
<label x="0" y="53.34" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="-MRW"/>
</segment>
<segment>
<wire x1="88.9" y1="53.34" x2="71.12" y2="53.34" width="0.1524" layer="91"/>
<label x="76.2" y="53.34" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="-MRW"/>
</segment>
<segment>
<wire x1="127" y1="53.34" x2="109.22" y2="53.34" width="0.1524" layer="91"/>
<label x="114.3" y="53.34" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="-MRW"/>
</segment>
<segment>
<wire x1="165.1" y1="53.34" x2="147.32" y2="53.34" width="0.1524" layer="91"/>
<label x="152.4" y="53.34" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="-MRW"/>
</segment>
</net>
<net name="A0" class="0">
<segment>
<wire x1="-25.4" y1="50.8" x2="-43.18" y2="50.8" width="0.1524" layer="91"/>
<label x="-38.1" y="50.8" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="A0"/>
</segment>
<segment>
<wire x1="50.8" y1="50.8" x2="33.02" y2="50.8" width="0.1524" layer="91"/>
<label x="38.1" y="50.8" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="A0"/>
</segment>
<segment>
<wire x1="12.7" y1="50.8" x2="-5.08" y2="50.8" width="0.1524" layer="91"/>
<label x="0" y="50.8" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="A0"/>
</segment>
<segment>
<wire x1="88.9" y1="50.8" x2="71.12" y2="50.8" width="0.1524" layer="91"/>
<label x="76.2" y="50.8" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="A0"/>
</segment>
<segment>
<wire x1="127" y1="50.8" x2="109.22" y2="50.8" width="0.1524" layer="91"/>
<label x="114.3" y="50.8" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="A0"/>
</segment>
<segment>
<wire x1="165.1" y1="50.8" x2="147.32" y2="50.8" width="0.1524" layer="91"/>
<label x="152.4" y="50.8" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="A0"/>
</segment>
</net>
<net name="A1" class="0">
<segment>
<wire x1="-25.4" y1="48.26" x2="-43.18" y2="48.26" width="0.1524" layer="91"/>
<label x="-38.1" y="48.26" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="A1"/>
</segment>
<segment>
<wire x1="50.8" y1="48.26" x2="33.02" y2="48.26" width="0.1524" layer="91"/>
<label x="38.1" y="48.26" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="A1"/>
</segment>
<segment>
<wire x1="12.7" y1="48.26" x2="-5.08" y2="48.26" width="0.1524" layer="91"/>
<label x="0" y="48.26" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="A1"/>
</segment>
<segment>
<wire x1="88.9" y1="48.26" x2="71.12" y2="48.26" width="0.1524" layer="91"/>
<label x="76.2" y="48.26" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="A1"/>
</segment>
<segment>
<wire x1="127" y1="48.26" x2="109.22" y2="48.26" width="0.1524" layer="91"/>
<label x="114.3" y="48.26" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="A1"/>
</segment>
<segment>
<wire x1="165.1" y1="48.26" x2="147.32" y2="48.26" width="0.1524" layer="91"/>
<label x="152.4" y="48.26" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="A1"/>
</segment>
</net>
<net name="A2" class="0">
<segment>
<wire x1="-25.4" y1="45.72" x2="-43.18" y2="45.72" width="0.1524" layer="91"/>
<label x="-38.1" y="45.72" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="A2"/>
</segment>
<segment>
<wire x1="50.8" y1="45.72" x2="33.02" y2="45.72" width="0.1524" layer="91"/>
<label x="38.1" y="45.72" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="A2"/>
</segment>
<segment>
<wire x1="12.7" y1="45.72" x2="-5.08" y2="45.72" width="0.1524" layer="91"/>
<label x="0" y="45.72" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="A2"/>
</segment>
<segment>
<wire x1="88.9" y1="45.72" x2="71.12" y2="45.72" width="0.1524" layer="91"/>
<label x="76.2" y="45.72" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="A2"/>
</segment>
<segment>
<wire x1="127" y1="45.72" x2="109.22" y2="45.72" width="0.1524" layer="91"/>
<label x="114.3" y="45.72" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="A2"/>
</segment>
<segment>
<wire x1="165.1" y1="45.72" x2="147.32" y2="45.72" width="0.1524" layer="91"/>
<label x="152.4" y="45.72" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="A2"/>
</segment>
</net>
<net name="A3" class="0">
<segment>
<wire x1="-25.4" y1="43.18" x2="-43.18" y2="43.18" width="0.1524" layer="91"/>
<label x="-38.1" y="43.18" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="A3"/>
</segment>
<segment>
<wire x1="50.8" y1="43.18" x2="33.02" y2="43.18" width="0.1524" layer="91"/>
<label x="38.1" y="43.18" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="A3"/>
</segment>
<segment>
<wire x1="12.7" y1="43.18" x2="-5.08" y2="43.18" width="0.1524" layer="91"/>
<label x="0" y="43.18" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="A3"/>
</segment>
<segment>
<wire x1="88.9" y1="43.18" x2="71.12" y2="43.18" width="0.1524" layer="91"/>
<label x="76.2" y="43.18" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="A3"/>
</segment>
<segment>
<wire x1="127" y1="43.18" x2="109.22" y2="43.18" width="0.1524" layer="91"/>
<label x="114.3" y="43.18" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="A3"/>
</segment>
<segment>
<wire x1="165.1" y1="43.18" x2="147.32" y2="43.18" width="0.1524" layer="91"/>
<label x="152.4" y="43.18" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="A3"/>
</segment>
</net>
<net name="A4" class="0">
<segment>
<wire x1="-25.4" y1="40.64" x2="-43.18" y2="40.64" width="0.1524" layer="91"/>
<label x="-38.1" y="40.64" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="A4"/>
</segment>
<segment>
<wire x1="50.8" y1="40.64" x2="33.02" y2="40.64" width="0.1524" layer="91"/>
<label x="38.1" y="40.64" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="A4"/>
</segment>
<segment>
<wire x1="12.7" y1="40.64" x2="-5.08" y2="40.64" width="0.1524" layer="91"/>
<label x="0" y="40.64" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="A4"/>
</segment>
<segment>
<wire x1="88.9" y1="40.64" x2="71.12" y2="40.64" width="0.1524" layer="91"/>
<label x="76.2" y="40.64" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="A4"/>
</segment>
<segment>
<wire x1="127" y1="40.64" x2="109.22" y2="40.64" width="0.1524" layer="91"/>
<label x="114.3" y="40.64" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="A4"/>
</segment>
<segment>
<wire x1="165.1" y1="40.64" x2="147.32" y2="40.64" width="0.1524" layer="91"/>
<label x="152.4" y="40.64" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="A4"/>
</segment>
</net>
<net name="A5" class="0">
<segment>
<wire x1="-25.4" y1="38.1" x2="-43.18" y2="38.1" width="0.1524" layer="91"/>
<label x="-38.1" y="38.1" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="A5"/>
</segment>
<segment>
<wire x1="50.8" y1="38.1" x2="33.02" y2="38.1" width="0.1524" layer="91"/>
<label x="38.1" y="38.1" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="A5"/>
</segment>
<segment>
<wire x1="12.7" y1="38.1" x2="-5.08" y2="38.1" width="0.1524" layer="91"/>
<label x="0" y="38.1" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="A5"/>
</segment>
<segment>
<wire x1="88.9" y1="38.1" x2="71.12" y2="38.1" width="0.1524" layer="91"/>
<label x="76.2" y="38.1" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="A5"/>
</segment>
<segment>
<wire x1="127" y1="38.1" x2="109.22" y2="38.1" width="0.1524" layer="91"/>
<label x="114.3" y="38.1" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="A5"/>
</segment>
<segment>
<wire x1="165.1" y1="38.1" x2="147.32" y2="38.1" width="0.1524" layer="91"/>
<label x="152.4" y="38.1" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="A5"/>
</segment>
</net>
<net name="A6" class="0">
<segment>
<wire x1="-25.4" y1="35.56" x2="-43.18" y2="35.56" width="0.1524" layer="91"/>
<label x="-38.1" y="35.56" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="A6"/>
</segment>
<segment>
<wire x1="50.8" y1="35.56" x2="33.02" y2="35.56" width="0.1524" layer="91"/>
<label x="38.1" y="35.56" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="A6"/>
</segment>
<segment>
<wire x1="12.7" y1="35.56" x2="-5.08" y2="35.56" width="0.1524" layer="91"/>
<label x="0" y="35.56" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="A6"/>
</segment>
<segment>
<wire x1="88.9" y1="35.56" x2="71.12" y2="35.56" width="0.1524" layer="91"/>
<label x="76.2" y="35.56" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="A6"/>
</segment>
<segment>
<wire x1="127" y1="35.56" x2="109.22" y2="35.56" width="0.1524" layer="91"/>
<label x="114.3" y="35.56" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="A6"/>
</segment>
<segment>
<wire x1="165.1" y1="35.56" x2="147.32" y2="35.56" width="0.1524" layer="91"/>
<label x="152.4" y="35.56" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="A6"/>
</segment>
</net>
<net name="A7" class="0">
<segment>
<wire x1="-25.4" y1="33.02" x2="-43.18" y2="33.02" width="0.1524" layer="91"/>
<label x="-38.1" y="33.02" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="A7"/>
</segment>
<segment>
<wire x1="50.8" y1="33.02" x2="33.02" y2="33.02" width="0.1524" layer="91"/>
<label x="38.1" y="33.02" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="A7"/>
</segment>
<segment>
<wire x1="12.7" y1="33.02" x2="-5.08" y2="33.02" width="0.1524" layer="91"/>
<label x="0" y="33.02" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="A7"/>
</segment>
<segment>
<wire x1="88.9" y1="33.02" x2="71.12" y2="33.02" width="0.1524" layer="91"/>
<label x="76.2" y="33.02" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="A7"/>
</segment>
<segment>
<wire x1="127" y1="33.02" x2="109.22" y2="33.02" width="0.1524" layer="91"/>
<label x="114.3" y="33.02" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="A7"/>
</segment>
<segment>
<wire x1="165.1" y1="33.02" x2="147.32" y2="33.02" width="0.1524" layer="91"/>
<label x="152.4" y="33.02" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="A7"/>
</segment>
</net>
<net name="INT" class="0">
<segment>
<wire x1="-25.4" y1="30.48" x2="-43.18" y2="30.48" width="0.1524" layer="91"/>
<label x="-38.1" y="30.48" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="-INT"/>
</segment>
<segment>
<wire x1="50.8" y1="30.48" x2="33.02" y2="30.48" width="0.1524" layer="91"/>
<label x="38.1" y="30.48" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="-INT"/>
</segment>
<segment>
<wire x1="12.7" y1="30.48" x2="-5.08" y2="30.48" width="0.1524" layer="91"/>
<label x="0" y="30.48" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="-INT"/>
</segment>
<segment>
<wire x1="88.9" y1="30.48" x2="71.12" y2="30.48" width="0.1524" layer="91"/>
<label x="76.2" y="30.48" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="-INT"/>
</segment>
<segment>
<wire x1="127" y1="30.48" x2="109.22" y2="30.48" width="0.1524" layer="91"/>
<label x="114.3" y="30.48" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="-INT"/>
</segment>
<segment>
<wire x1="165.1" y1="30.48" x2="147.32" y2="30.48" width="0.1524" layer="91"/>
<label x="152.4" y="30.48" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="-INT"/>
</segment>
</net>
<net name="N2" class="0">
<segment>
<wire x1="-25.4" y1="27.94" x2="-43.18" y2="27.94" width="0.1524" layer="91"/>
<label x="-38.1" y="27.94" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="N2"/>
</segment>
<segment>
<wire x1="50.8" y1="27.94" x2="33.02" y2="27.94" width="0.1524" layer="91"/>
<label x="38.1" y="27.94" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="N2"/>
</segment>
<segment>
<wire x1="12.7" y1="27.94" x2="-5.08" y2="27.94" width="0.1524" layer="91"/>
<label x="0" y="27.94" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="N2"/>
</segment>
<segment>
<wire x1="88.9" y1="27.94" x2="71.12" y2="27.94" width="0.1524" layer="91"/>
<label x="76.2" y="27.94" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="N2"/>
</segment>
<segment>
<wire x1="127" y1="27.94" x2="109.22" y2="27.94" width="0.1524" layer="91"/>
<label x="114.3" y="27.94" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="N2"/>
</segment>
<segment>
<wire x1="165.1" y1="27.94" x2="147.32" y2="27.94" width="0.1524" layer="91"/>
<label x="152.4" y="27.94" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="N2"/>
</segment>
</net>
<net name="EF" class="0">
<segment>
<wire x1="-25.4" y1="25.4" x2="-43.18" y2="25.4" width="0.1524" layer="91"/>
<label x="-38.1" y="25.4" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="-EF"/>
</segment>
<segment>
<wire x1="50.8" y1="25.4" x2="33.02" y2="25.4" width="0.1524" layer="91"/>
<label x="38.1" y="25.4" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="-EF"/>
</segment>
<segment>
<wire x1="12.7" y1="25.4" x2="-5.08" y2="25.4" width="0.1524" layer="91"/>
<label x="0" y="25.4" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="-EF"/>
</segment>
<segment>
<wire x1="88.9" y1="25.4" x2="71.12" y2="25.4" width="0.1524" layer="91"/>
<label x="76.2" y="25.4" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="-EF"/>
</segment>
<segment>
<wire x1="127" y1="25.4" x2="109.22" y2="25.4" width="0.1524" layer="91"/>
<label x="114.3" y="25.4" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="-EF"/>
</segment>
<segment>
<wire x1="165.1" y1="25.4" x2="147.32" y2="25.4" width="0.1524" layer="91"/>
<label x="152.4" y="25.4" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="-EF"/>
</segment>
</net>
<net name="VMA" class="0">
<segment>
<wire x1="-25.4" y1="22.86" x2="-43.18" y2="22.86" width="0.1524" layer="91"/>
<label x="-38.1" y="22.86" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="-VMA"/>
</segment>
<segment>
<wire x1="50.8" y1="22.86" x2="33.02" y2="22.86" width="0.1524" layer="91"/>
<label x="38.1" y="22.86" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="-VMA"/>
</segment>
<segment>
<wire x1="12.7" y1="22.86" x2="-5.08" y2="22.86" width="0.1524" layer="91"/>
<label x="0" y="22.86" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="-VMA"/>
</segment>
<segment>
<wire x1="88.9" y1="22.86" x2="71.12" y2="22.86" width="0.1524" layer="91"/>
<label x="76.2" y="22.86" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="-VMA"/>
</segment>
<segment>
<wire x1="127" y1="22.86" x2="109.22" y2="22.86" width="0.1524" layer="91"/>
<label x="114.3" y="22.86" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="-VMA"/>
</segment>
<segment>
<wire x1="165.1" y1="22.86" x2="147.32" y2="22.86" width="0.1524" layer="91"/>
<label x="152.4" y="22.86" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="-VMA"/>
</segment>
</net>
<net name="RESET" class="0">
<segment>
<wire x1="-25.4" y1="20.32" x2="-43.18" y2="20.32" width="0.1524" layer="91"/>
<label x="-38.1" y="20.32" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="-RESET"/>
</segment>
<segment>
<wire x1="50.8" y1="20.32" x2="33.02" y2="20.32" width="0.1524" layer="91"/>
<label x="38.1" y="20.32" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="-RESET"/>
</segment>
<segment>
<wire x1="12.7" y1="20.32" x2="-5.08" y2="20.32" width="0.1524" layer="91"/>
<label x="0" y="20.32" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="-RESET"/>
</segment>
<segment>
<wire x1="88.9" y1="20.32" x2="71.12" y2="20.32" width="0.1524" layer="91"/>
<label x="76.2" y="20.32" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="-RESET"/>
</segment>
<segment>
<wire x1="127" y1="20.32" x2="109.22" y2="20.32" width="0.1524" layer="91"/>
<label x="114.3" y="20.32" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="-RESET"/>
</segment>
<segment>
<wire x1="165.1" y1="20.32" x2="147.32" y2="20.32" width="0.1524" layer="91"/>
<label x="152.4" y="20.32" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="-RESET"/>
</segment>
</net>
<net name="N1" class="0">
<segment>
<wire x1="-25.4" y1="17.78" x2="-43.18" y2="17.78" width="0.1524" layer="91"/>
<label x="-38.1" y="17.78" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="N1"/>
</segment>
<segment>
<wire x1="50.8" y1="17.78" x2="33.02" y2="17.78" width="0.1524" layer="91"/>
<label x="38.1" y="17.78" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="N1"/>
</segment>
<segment>
<wire x1="12.7" y1="17.78" x2="-5.08" y2="17.78" width="0.1524" layer="91"/>
<label x="0" y="17.78" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="N1"/>
</segment>
<segment>
<wire x1="88.9" y1="17.78" x2="71.12" y2="17.78" width="0.1524" layer="91"/>
<label x="76.2" y="17.78" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="N1"/>
</segment>
<segment>
<wire x1="127" y1="17.78" x2="109.22" y2="17.78" width="0.1524" layer="91"/>
<label x="114.3" y="17.78" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="N1"/>
</segment>
<segment>
<wire x1="165.1" y1="17.78" x2="147.32" y2="17.78" width="0.1524" layer="91"/>
<label x="152.4" y="17.78" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="N1"/>
</segment>
</net>
<net name="N0" class="0">
<segment>
<wire x1="-25.4" y1="15.24" x2="-43.18" y2="15.24" width="0.1524" layer="91"/>
<label x="-38.1" y="15.24" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="N0"/>
</segment>
<segment>
<wire x1="50.8" y1="15.24" x2="33.02" y2="15.24" width="0.1524" layer="91"/>
<label x="38.1" y="15.24" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="N0"/>
</segment>
<segment>
<wire x1="12.7" y1="15.24" x2="-5.08" y2="15.24" width="0.1524" layer="91"/>
<label x="0" y="15.24" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="N0"/>
</segment>
<segment>
<wire x1="88.9" y1="15.24" x2="71.12" y2="15.24" width="0.1524" layer="91"/>
<label x="76.2" y="15.24" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="N0"/>
</segment>
<segment>
<wire x1="127" y1="15.24" x2="109.22" y2="15.24" width="0.1524" layer="91"/>
<label x="114.3" y="15.24" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="N0"/>
</segment>
<segment>
<wire x1="165.1" y1="15.24" x2="147.32" y2="15.24" width="0.1524" layer="91"/>
<label x="152.4" y="15.24" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="N0"/>
</segment>
</net>
<net name="GND" class="0">
<segment>
<wire x1="-25.4" y1="12.7" x2="-43.18" y2="12.7" width="0.1524" layer="91"/>
<label x="-38.1" y="12.7" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="GND"/>
</segment>
<segment>
<wire x1="50.8" y1="12.7" x2="33.02" y2="12.7" width="0.1524" layer="91"/>
<label x="38.1" y="12.7" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="GND"/>
</segment>
<segment>
<wire x1="12.7" y1="12.7" x2="-5.08" y2="12.7" width="0.1524" layer="91"/>
<label x="0" y="12.7" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="GND"/>
</segment>
<segment>
<wire x1="88.9" y1="12.7" x2="71.12" y2="12.7" width="0.1524" layer="91"/>
<label x="76.2" y="12.7" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="GND"/>
</segment>
<segment>
<wire x1="127" y1="12.7" x2="109.22" y2="12.7" width="0.1524" layer="91"/>
<label x="114.3" y="12.7" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="GND"/>
</segment>
<segment>
<wire x1="165.1" y1="12.7" x2="147.32" y2="12.7" width="0.1524" layer="91"/>
<label x="152.4" y="12.7" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="GND"/>
</segment>
</net>
<net name="EF1" class="0">
<segment>
<wire x1="-25.4" y1="93.98" x2="-43.18" y2="93.98" width="0.1524" layer="91"/>
<label x="-33.02" y="93.98" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="-EF1"/>
</segment>
<segment>
<wire x1="50.8" y1="93.98" x2="33.02" y2="93.98" width="0.1524" layer="91"/>
<label x="38.1" y="93.98" size="1.778" layer="95"/>
<label x="38.1" y="93.98" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="-EF1"/>
</segment>
<segment>
<wire x1="12.7" y1="93.98" x2="-5.08" y2="93.98" width="0.1524" layer="91"/>
<label x="0" y="93.98" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="-EF1"/>
</segment>
<segment>
<wire x1="88.9" y1="93.98" x2="71.12" y2="93.98" width="0.1524" layer="91"/>
<label x="76.2" y="93.98" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="-EF1"/>
</segment>
<segment>
<wire x1="127" y1="93.98" x2="109.22" y2="93.98" width="0.1524" layer="91"/>
<label x="119.38" y="93.98" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="-EF1"/>
</segment>
<segment>
<wire x1="165.1" y1="93.98" x2="147.32" y2="93.98" width="0.1524" layer="91"/>
<label x="152.4" y="93.98" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="-EF1"/>
</segment>
</net>
<net name="EF2" class="0">
<segment>
<wire x1="-25.4" y1="91.44" x2="-43.18" y2="91.44" width="0.1524" layer="91"/>
<label x="-33.02" y="91.44" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="-EF2"/>
</segment>
<segment>
<wire x1="50.8" y1="91.44" x2="33.02" y2="91.44" width="0.1524" layer="91"/>
<label x="38.1" y="91.44" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="-EF2"/>
</segment>
<segment>
<wire x1="12.7" y1="91.44" x2="-5.08" y2="91.44" width="0.1524" layer="91"/>
<label x="0" y="91.44" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="-EF2"/>
</segment>
<segment>
<wire x1="88.9" y1="91.44" x2="71.12" y2="91.44" width="0.1524" layer="91"/>
<label x="76.2" y="91.44" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="-EF2"/>
</segment>
<segment>
<wire x1="127" y1="91.44" x2="109.22" y2="91.44" width="0.1524" layer="91"/>
<label x="119.38" y="91.44" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="-EF2"/>
</segment>
<segment>
<wire x1="165.1" y1="91.44" x2="147.32" y2="91.44" width="0.1524" layer="91"/>
<label x="152.4" y="91.44" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="-EF2"/>
</segment>
</net>
<net name="EF3" class="0">
<segment>
<wire x1="-25.4" y1="88.9" x2="-43.18" y2="88.9" width="0.1524" layer="91"/>
<label x="-33.02" y="88.9" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="-EF3"/>
</segment>
<segment>
<wire x1="50.8" y1="88.9" x2="33.02" y2="88.9" width="0.1524" layer="91"/>
<label x="38.1" y="88.9" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="-EF3"/>
</segment>
<segment>
<wire x1="12.7" y1="88.9" x2="-5.08" y2="88.9" width="0.1524" layer="91"/>
<label x="0" y="88.9" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="-EF3"/>
</segment>
<segment>
<wire x1="88.9" y1="88.9" x2="71.12" y2="88.9" width="0.1524" layer="91"/>
<label x="76.2" y="88.9" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="-EF3"/>
</segment>
<segment>
<wire x1="127" y1="88.9" x2="109.22" y2="88.9" width="0.1524" layer="91"/>
<label x="119.38" y="88.9" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="-EF3"/>
</segment>
<segment>
<wire x1="165.1" y1="88.9" x2="147.32" y2="88.9" width="0.1524" layer="91"/>
<label x="152.4" y="88.9" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="-EF3"/>
</segment>
</net>
<net name="INP" class="0">
<segment>
<wire x1="-25.4" y1="10.16" x2="-43.18" y2="10.16" width="0.1524" layer="91"/>
<label x="-38.1" y="10.16" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="-INP"/>
</segment>
<segment>
<wire x1="50.8" y1="10.16" x2="33.02" y2="10.16" width="0.1524" layer="91"/>
<label x="38.1" y="10.16" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="-INP"/>
</segment>
<segment>
<wire x1="12.7" y1="10.16" x2="-5.08" y2="10.16" width="0.1524" layer="91"/>
<label x="0" y="10.16" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="-INP"/>
</segment>
<segment>
<wire x1="88.9" y1="10.16" x2="71.12" y2="10.16" width="0.1524" layer="91"/>
<label x="76.2" y="10.16" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="-INP"/>
</segment>
<segment>
<wire x1="127" y1="10.16" x2="109.22" y2="10.16" width="0.1524" layer="91"/>
<label x="114.3" y="10.16" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="-INP"/>
</segment>
<segment>
<wire x1="165.1" y1="10.16" x2="147.32" y2="10.16" width="0.1524" layer="91"/>
<label x="152.4" y="10.16" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="-INP"/>
</segment>
</net>
<net name="OUT" class="0">
<segment>
<wire x1="-25.4" y1="7.62" x2="-43.18" y2="7.62" width="0.1524" layer="91"/>
<label x="-38.1" y="7.62" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="-OUT"/>
</segment>
<segment>
<wire x1="50.8" y1="7.62" x2="33.02" y2="7.62" width="0.1524" layer="91"/>
<label x="38.1" y="7.62" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="-OUT"/>
</segment>
<segment>
<wire x1="12.7" y1="7.62" x2="-5.08" y2="7.62" width="0.1524" layer="91"/>
<label x="0" y="7.62" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="-OUT"/>
</segment>
<segment>
<wire x1="88.9" y1="7.62" x2="71.12" y2="7.62" width="0.1524" layer="91"/>
<label x="76.2" y="7.62" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="-OUT"/>
</segment>
<segment>
<wire x1="127" y1="7.62" x2="109.22" y2="7.62" width="0.1524" layer="91"/>
<label x="114.3" y="7.62" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="-OUT"/>
</segment>
<segment>
<wire x1="165.1" y1="7.62" x2="147.32" y2="7.62" width="0.1524" layer="91"/>
<label x="152.4" y="7.62" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="-OUT"/>
</segment>
</net>
<net name="EXP" class="0">
<segment>
<wire x1="-25.4" y1="5.08" x2="-43.18" y2="5.08" width="0.1524" layer="91"/>
<label x="-38.1" y="5.08" size="1.778" layer="95"/>
<pinref part="U$1" gate="G$1" pin="EXP"/>
</segment>
<segment>
<wire x1="50.8" y1="5.08" x2="33.02" y2="5.08" width="0.1524" layer="91"/>
<label x="38.1" y="5.08" size="1.778" layer="95"/>
<pinref part="U$2" gate="G$1" pin="EXP"/>
</segment>
<segment>
<wire x1="12.7" y1="5.08" x2="-5.08" y2="5.08" width="0.1524" layer="91"/>
<label x="0" y="5.08" size="1.778" layer="95"/>
<pinref part="U$3" gate="G$1" pin="EXP"/>
</segment>
<segment>
<wire x1="88.9" y1="5.08" x2="71.12" y2="5.08" width="0.1524" layer="91"/>
<label x="76.2" y="5.08" size="1.778" layer="95"/>
<pinref part="U$4" gate="G$1" pin="EXP"/>
</segment>
<segment>
<wire x1="127" y1="5.08" x2="109.22" y2="5.08" width="0.1524" layer="91"/>
<label x="114.3" y="5.08" size="1.778" layer="95"/>
<pinref part="U$5" gate="G$1" pin="EXP"/>
</segment>
<segment>
<wire x1="165.1" y1="5.08" x2="147.32" y2="5.08" width="0.1524" layer="91"/>
<label x="152.4" y="5.08" size="1.778" layer="95"/>
<pinref part="U$6" gate="G$1" pin="EXP"/>
</segment>
</net>
</nets>
</sheet>
</sheets>
</schematic>
</drawing>
</eagle>
