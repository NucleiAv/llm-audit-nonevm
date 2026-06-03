use anchor_lang::prelude::*;
use anchor_lang::solana_program::program_error::ProgramError;

declare_id!("BUMP1111111111111111111111111111111111111111");

#[program]
pub mod bump_vuln {
    use super::*;

    pub fn create_config(ctx: Context<CreateConfig>, user_supplied_bump: u8) -> Result<()> {
        let seeds = &[b"config".as_ref(), &[user_supplied_bump]];

        let (derived_key, _) =
            anchor_lang::solana_program::pubkey::Pubkey::find_program_address(
                &[b"config"],
                ctx.program_id,
            );

        require!(
            ctx.accounts.config.key() == derived_key || {
                let alt = anchor_lang::solana_program::pubkey::Pubkey::create_program_address(
                    seeds,
                    ctx.program_id,
                )
                .map_err(|_| error!(BumpError::InvalidBump))?;
                ctx.accounts.config.key() == alt
            },
            BumpError::InvalidBump
        );

        let config = &mut ctx.accounts.config;
        config.bump = user_supplied_bump;
        config.authority = ctx.accounts.payer.key();
        Ok(())
    }
}

#[derive(Accounts)]
pub struct CreateConfig<'info> {
    #[account(mut)]
    pub config: AccountInfo<'info>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[account]
pub struct Config {
    pub bump: u8,
    pub authority: Pubkey,
}

#[error_code]
pub enum BumpError {
    #[msg("Invalid bump seed")]
    InvalidBump,
}
