Shader "NeonProtocol/NeonHologram"
{
    Properties
    {
        _BaseColor ("Base Color", Color) = (1, 0, 1, 0.5)
        _ScanlineSpeed ("Scanline Speed", Float) = 2.0
        _ScanlineCount ("Scanline Density", Float) = 80.0
        _ScanlineIntensity ("Scanline Intensity", Range(0, 1)) = 0.3
        _FlickerSpeed ("Flicker Speed", Float) = 15.0
        _FlickerIntensity ("Flicker Intensity", Range(0, 1)) = 0.1
        _EmissionIntensity ("Emission Intensity", Range(0, 10)) = 2.0
        _FresnelPower ("Fresnel Power", Range(0.5, 5)) = 2.0
        _FresnelColor ("Fresnel Color", Color) = (0, 1, 1, 1)
        _GlitchIntensity ("Glitch Intensity", Range(0, 0.1)) = 0.01
    }

    SubShader
    {
        Tags
        {
            "RenderType" = "Transparent"
            "RenderPipeline" = "UniversalPipeline"
            "Queue" = "Transparent"
        }

        Blend SrcAlpha OneMinusSrcAlpha
        ZWrite Off
        Cull Back

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode" = "UniversalForward" }

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float2 uv : TEXCOORD0;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float2 uv : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float3 viewDirWS : TEXCOORD2;
                float3 positionWS : TEXCOORD3;
            };

            CBUFFER_START(UnityPerMaterial)
                half4 _BaseColor;
                float _ScanlineSpeed;
                float _ScanlineCount;
                float _ScanlineIntensity;
                float _FlickerSpeed;
                float _FlickerIntensity;
                float _EmissionIntensity;
                float _FresnelPower;
                half4 _FresnelColor;
                float _GlitchIntensity;
            CBUFFER_END

            Varyings vert(Attributes input)
            {
                Varyings output;
                VertexPositionInputs posInputs = GetVertexPositionInputs(input.positionOS.xyz);
                VertexNormalInputs normInputs = GetVertexNormalInputs(input.normalOS);

                // Glitch: random vertex displacement
                float glitchTime = floor(_Time.y * 20.0);
                float glitch = step(0.95, frac(sin(glitchTime * 43758.5453) * 2.0));
                float3 offset = float3(glitch * _GlitchIntensity * sin(_Time.y * 100.0), 0, 0);

                output.positionCS = posInputs.positionCS + float4(offset, 0);
                output.positionWS = posInputs.positionWS;
                output.normalWS = normInputs.normalWS;
                output.viewDirWS = GetWorldSpaceNormalizeViewDir(posInputs.positionWS);
                output.uv = input.uv;
                return output;
            }

            half4 frag(Varyings input) : SV_Target
            {
                // Scanlines
                float scanline = sin((input.positionWS.y + _Time.y * _ScanlineSpeed) * _ScanlineCount) * 0.5 + 0.5;
                scanline = lerp(1.0, scanline, _ScanlineIntensity);

                // Flicker
                float flicker = 1.0 - _FlickerIntensity * step(0.9, frac(sin(_Time.y * _FlickerSpeed) * 43758.5453));

                // Fresnel rim glow
                float NdotV = saturate(dot(normalize(input.normalWS), normalize(input.viewDirWS)));
                float fresnel = pow(1.0 - NdotV, _FresnelPower);
                half3 fresnelColor = _FresnelColor.rgb * fresnel * _EmissionIntensity;

                // Composite
                half3 color = _BaseColor.rgb * _EmissionIntensity * scanline * flicker;
                color += fresnelColor;

                float alpha = _BaseColor.a * scanline * flicker;
                alpha = saturate(alpha + fresnel * 0.5);

                return half4(color, alpha);
            }
            ENDHLSL
        }
    }

    FallBack "Universal Render Pipeline/Unlit"
}
