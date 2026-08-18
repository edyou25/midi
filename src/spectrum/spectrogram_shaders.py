VERTEX_BODY = r"""
layout(location = 0) in vec2 aUV;

uniform sampler2D uSpectrum;
uniform mat4 uMVP;
uniform float uHeight;
uniform vec2 uTexel;

out float vMagnitude;
out float vAge;
out vec3 vNormal;

float sampleMagnitude(vec2 uv)
{
    return texture(
        uSpectrum,
        clamp(uv, vec2(0.0), vec2(1.0))
    ).r;
}

void main()
{
    float m = sampleMagnitude(aUV);

    float leftM = sampleMagnitude(
        vec2(max(aUV.x - uTexel.x, 0.0), aUV.y)
    );
    float rightM = sampleMagnitude(
        vec2(min(aUV.x + uTexel.x, 1.0), aUV.y)
    );
    float oldM = sampleMagnitude(
        vec2(aUV.x, max(aUV.y - uTexel.y, 0.0))
    );
    float newM = sampleMagnitude(
        vec2(aUV.x, min(aUV.y + uTexel.y, 1.0))
    );

    float h = pow(max(m, 0.0), 1.35) * uHeight;

    vec3 position = vec3(
        (aUV.y - 0.5) * 6.0,   // time: left -> right
        h - 0.85,              // height
        (0.5 - aUV.x) * 1.4    // frequency: shallow depth
    );

    float dx = (rightM - leftM) * uHeight * 3.0;
    float dz = (newM - oldM) * uHeight * 2.0;

    vNormal = normalize(vec3(-dx, 0.45, -dz));
    vMagnitude = m;
    vAge = aUV.y;

    gl_Position = uMVP * vec4(position, 1.0);
}
"""


FRAGMENT_BODY = r"""
in float vMagnitude;
in float vAge;
in vec3 vNormal;

out vec4 fragColor;

vec3 palette(float x)
{
    vec3 c0 = vec3(0.015, 0.010, 0.080);
    vec3 c1 = vec3(0.080, 0.100, 0.550);
    vec3 c2 = vec3(0.000, 0.750, 0.950);
    vec3 c3 = vec3(0.950, 0.900, 0.150);
    vec3 c4 = vec3(1.000, 0.180, 0.020);

    if (x < 0.25)
        return mix(c0, c1, x / 0.25);
    if (x < 0.50)
        return mix(c1, c2, (x - 0.25) / 0.25);
    if (x < 0.75)
        return mix(c2, c3, (x - 0.50) / 0.25);

    return mix(c3, c4, (x - 0.75) / 0.25);
}

void main()
{
    vec3 lightDir = normalize(vec3(-0.35, 0.85, 0.45));
    float diffuse = max(dot(normalize(vNormal), lightDir), 0.0);
    float lighting = 0.30 + 0.70 * diffuse;
    float ageFade = mix(0.42, 1.0, vAge);

    vec3 color = palette(vMagnitude);
    color *= lighting * ageFade;
    fragColor = vec4(color, 1.0);
}
"""


def shader_sources(is_gles):
    if is_gles:
        header = (
            "#version 300 es\n"
            "precision highp float;\n"
            "precision highp int;\n"
        )
    else:
        header = "#version 330 core\n"

    return header + VERTEX_BODY, header + FRAGMENT_BODY
